import atexit
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, LiteralString, Optional, cast

from fastmcp import FastMCP
from neo4j import GraphDatabase, Query
from neo4j.exceptions import AuthError, CypherSyntaxError, Neo4jError, ServiceUnavailable

sys.path.insert(0, str(Path(__file__).parent))

from config_loader import load_server_config, run_server

config = load_server_config("knowledge_graph")
mcp = FastMCP("Neo4jMemoryBank")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
QUERY_TIMEOUT_SECONDS = float(os.getenv("NEO4J_QUERY_TIMEOUT_SECONDS", "6"))
DEFAULT_LIMIT = int(os.getenv("KG_DEFAULT_LIMIT", "20"))
MAX_LIMIT = int(os.getenv("KG_MAX_LIMIT", "100"))

_RELATION_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")


def _response(
    success: bool,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    error_code: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "success": success,
        "message": message,
        "data": data or {},
        "error_code": error_code,
    }


def _normalize_limit(limit: int) -> int:
    if limit <= 0:
        return DEFAULT_LIMIT
    return min(limit, MAX_LIMIT)


class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str, database: str):
        self.uri = uri
        self.user = user
        self.database = database
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def health_check(self) -> Dict[str, Any]:
        self.driver.verify_connectivity()
        return {"uri": self.uri, "database": self.database}

    def query(
        self,
        cypher: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: float = QUERY_TIMEOUT_SECONDS,
    ) -> List[Dict[str, Any]]:
        with self.driver.session(database=self.database) as session:
            query_obj = Query(cast(LiteralString, cypher))
            result = session.run(query_obj, parameters or {}, timeout=timeout)
            return [record.data() for record in result]


client = Neo4jClient(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE)
atexit.register(client.close)


def _map_neo4j_exception(exc: Exception) -> Dict[str, Any]:
    if isinstance(exc, ServiceUnavailable):
        return _response(False, "Neo4j service is unavailable.", error_code="neo4j_unavailable")
    if isinstance(exc, AuthError):
        return _response(False, "Neo4j authentication failed.", error_code="neo4j_auth_failed")
    if isinstance(exc, CypherSyntaxError):
        return _response(False, "Cypher syntax error.", error_code="cypher_syntax_error")
    if isinstance(exc, Neo4jError):
        return _response(False, f"Neo4j error: {exc.code}", error_code="neo4j_error")
    if isinstance(exc, TimeoutError):
        return _response(False, "Query timed out.", error_code="query_timeout")
    return _response(False, f"Unhandled error: {exc}", error_code="unknown_error")


def _validate_entity_value(value: str, field_name: str) -> Optional[Dict[str, Any]]:
    if not value or not value.strip():
        return _response(False, f"{field_name} cannot be empty.", error_code="invalid_argument")
    if len(value.strip()) > 256:
        return _response(False, f"{field_name} is too long.", error_code="invalid_argument")
    return None


def _validate_relation_name(relation: str) -> Optional[Dict[str, Any]]:
    if not _RELATION_NAME_PATTERN.match(relation):
        return _response(
            False,
            "relation must match ^[A-Za-z_][A-Za-z0-9_]{0,63}$",
            error_code="invalid_relation",
        )
    return None


@mcp.tool()
def health_check() -> Dict[str, Any]:
    """
    Verify Neo4j connectivity and return connection metadata.
    """
    try:
        details = client.health_check()
        return _response(True, "Neo4j connection is healthy.", data=details)
    except Exception as exc:
        return _map_neo4j_exception(exc)


@mcp.tool()
def query_graph(cypher: str, limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
    """
    Execute a read-only Cypher query.

    Args:
        cypher: Read-only Cypher statement, for example:
            MATCH (n)-[r]->(m) RETURN n, r, m
        limit: Max rows returned, clamped to KG_MAX_LIMIT.
    """
    if not cypher or not cypher.strip():
        return _response(False, "cypher cannot be empty.", error_code="invalid_argument")

    safe_limit = _normalize_limit(limit)
    final_query = f"{cypher.strip()} LIMIT $limit"
    try:
        rows = client.query(final_query, {"limit": safe_limit})
        return _response(
            True,
            "Read query completed.",
            data={"rows": rows, "count": len(rows), "limit": safe_limit},
        )
    except Exception as exc:
        return _map_neo4j_exception(exc)


@mcp.tool()
def add_memory(subject: str, relation: str, obj: str) -> Dict[str, Any]:
    """
    Upsert a memory triple using (:Entity)-[:RELATION]->(:Entity).
    """
    for field_name, field_value in (("subject", subject), ("relation", relation), ("obj", obj)):
        validation = _validate_entity_value(field_value, field_name)
        if validation:
            return validation
    relation_validation = _validate_relation_name(relation)
    if relation_validation:
        return relation_validation

    cypher = (
        "MERGE (s:Entity {name: $subject}) "
        "ON CREATE SET s.created_at = timestamp() "
        "MERGE (o:Entity {name: $obj}) "
        "ON CREATE SET o.created_at = timestamp() "
        "MERGE (s)-[r:RELATION {name: $relation}]->(o) "
        "ON CREATE SET r.created_at = timestamp() "
        "ON MATCH SET r.updated_at = timestamp() "
        "RETURN s.name AS subject, r.name AS relation, o.name AS obj, "
        "r.created_at IS NOT NULL AS relation_exists"
    )
    try:
        rows = client.query(cypher, {"subject": subject.strip(), "relation": relation.strip(), "obj": obj.strip()})
        return _response(True, "Memory upserted.", data={"rows": rows, "count": len(rows)})
    except Exception as exc:
        return _map_neo4j_exception(exc)


@mcp.tool()
def get_memories_for_subject(subject: str, limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
    """
    List outgoing memories for a subject entity.
    """
    validation = _validate_entity_value(subject, "subject")
    if validation:
        return validation

    safe_limit = _normalize_limit(limit)
    cypher = (
        "MATCH (s:Entity {name: $subject})-[r:RELATION]->(o:Entity) "
        "RETURN s.name AS subject, r.name AS relation, o.name AS obj "
        "LIMIT $limit"
    )
    try:
        rows = client.query(cypher, {"subject": subject.strip(), "limit": safe_limit})
        return _response(True, "Subject memories fetched.", data={"rows": rows, "count": len(rows)})
    except Exception as exc:
        return _map_neo4j_exception(exc)


@mcp.tool()
def search_entities(keyword: str, limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
    """
    Fuzzy search entities by name using CONTAINS.
    """
    validation = _validate_entity_value(keyword, "keyword")
    if validation:
        return validation

    safe_limit = _normalize_limit(limit)
    cypher = (
        "MATCH (e:Entity) "
        "WHERE toLower(e.name) CONTAINS toLower($keyword) "
        "RETURN e.name AS entity "
        "ORDER BY e.name "
        "LIMIT $limit"
    )
    try:
        rows = client.query(cypher, {"keyword": keyword.strip(), "limit": safe_limit})
        return _response(True, "Entity search completed.", data={"rows": rows, "count": len(rows)})
    except Exception as exc:
        return _map_neo4j_exception(exc)


@mcp.tool()
def get_neighbors(entity: str, depth: int = 1, limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
    """
    Expand neighbors from an entity with bounded depth.
    """
    validation = _validate_entity_value(entity, "entity")
    if validation:
        return validation
    if depth < 1 or depth > 3:
        return _response(False, "depth must be between 1 and 3.", error_code="invalid_argument")

    safe_limit = _normalize_limit(limit)
    cypher = (
        f"MATCH p=(s:Entity {{name: $entity}})-[:RELATION*1..{depth}]-(n:Entity) "
        "RETURN [node IN nodes(p) | node.name] AS path "
        "LIMIT $limit"
    )
    try:
        rows = client.query(cypher, {"entity": entity.strip(), "limit": safe_limit})
        return _response(True, "Neighbors fetched.", data={"rows": rows, "count": len(rows), "depth": depth})
    except Exception as exc:
        return _map_neo4j_exception(exc)


@mcp.tool()
def delete_memory(subject: str, relation: str, obj: str, dry_run: bool = True) -> Dict[str, Any]:
    """
    Delete a single memory triple. Use dry_run to preview matches first.
    """
    for field_name, field_value in (("subject", subject), ("relation", relation), ("obj", obj)):
        validation = _validate_entity_value(field_value, field_name)
        if validation:
            return validation

    match_cypher = (
        "MATCH (s:Entity {name: $subject})-[r:RELATION {name: $relation}]->(o:Entity {name: $obj}) "
        "RETURN count(r) AS matched"
    )
    try:
        precheck = client.query(
            match_cypher,
            {"subject": subject.strip(), "relation": relation.strip(), "obj": obj.strip()},
        )
        matched = int(precheck[0]["matched"]) if precheck else 0
        if dry_run:
            return _response(True, "Dry run completed.", data={"matched": matched, "will_delete": matched})
        if matched == 0:
            return _response(True, "No memory matched the triple.", data={"deleted": 0})

        delete_cypher = (
            "MATCH (s:Entity {name: $subject})-[r:RELATION {name: $relation}]->(o:Entity {name: $obj}) "
            "DELETE r "
            "RETURN count(*) AS deleted"
        )
        deleted_rows = client.query(
            delete_cypher,
            {"subject": subject.strip(), "relation": relation.strip(), "obj": obj.strip()},
        )
        deleted = int(deleted_rows[0]["deleted"]) if deleted_rows else 0
        return _response(True, "Memory deleted.", data={"deleted": deleted})
    except Exception as exc:
        return _map_neo4j_exception(exc)


@mcp.tool()
def execute_write_cypher(cypher: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute controlled write Cypher for advanced use cases.

    This tool executes custom write Cypher for advanced use cases.
    """
    if not cypher or not cypher.strip():
        return _response(False, "cypher cannot be empty.", error_code="invalid_argument")
    try:
        rows = client.query(cypher, parameters or {})
        return _response(True, "Write query completed.", data={"rows": rows, "count": len(rows)})
    except Exception as exc:
        return _map_neo4j_exception(exc)


if __name__ == "__main__":
    run_server(mcp, config)
