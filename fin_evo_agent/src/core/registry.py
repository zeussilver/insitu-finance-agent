"""Tool Registry for storing and retrieving tool artifacts.

Architecture: "Metadata in DB, Payload on Disk"
- Code files stored in data/artifacts/generated/
- Metadata stored in SQLite database
- Content-based deduplication via SHA256 hash
"""

import hashlib
from typing import Optional, List
from sqlmodel import Session, create_engine, select

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
from src.config import DB_URL, GENERATED_DIR, BOOTSTRAP_DIR
from src.core.models import ToolArtifact, ToolStatus, Permission, SQLModel


class ToolRegistry:
    """Registry for tool registration, storage, and retrieval."""

    def __init__(self, db_url: str = DB_URL):
        self.engine = create_engine(db_url)
        # Ensure tables exist
        SQLModel.metadata.create_all(self.engine)

    def _compute_hash(self, code: str) -> str:
        """Compute SHA256 hash of code content."""
        return hashlib.sha256(code.encode('utf-8')).hexdigest()

    def _generate_filename(self, name: str, version: str, content_hash: str) -> str:
        """Generate filename: {name}_v{version}_{hash8}.py"""
        hash8 = content_hash[:8]
        return f"{name}_v{version}_{hash8}.py"

    def register(
        self,
        name: str,
        code: str,
        args_schema: dict = None,
        permissions: List[str] = None,
        test_cases: List[dict] = None,
        is_bootstrap: bool = False
    ) -> ToolArtifact:
        """
        Register a new tool.

        Flow:
        1. Compute content hash (SHA256)
        2. Check if hash already exists (deduplication)
        3. Write code file to disk
        4. Insert metadata record to DB

        Args:
            name: Tool function name
            code: Python source code
            args_schema: JSON Schema for arguments
            permissions: List of Permission values
            test_cases: List of test case dicts
            is_bootstrap: If True, store in bootstrap/ instead of generated/

        Returns:
            ToolArtifact instance (existing or newly created)
        """
        content_hash = self._compute_hash(code)

        with Session(self.engine) as session:
            # Check for existing tool with same hash (deduplication)
            existing = session.exec(
                select(ToolArtifact).where(ToolArtifact.content_hash == content_hash)
            ).first()

            if existing:
                return existing

            # Check for existing tool with same name (versioning)
            same_name = session.exec(
                select(ToolArtifact).where(ToolArtifact.name == name)
            ).all()

            if same_name:
                # Increment version
                latest = max(same_name, key=lambda t: t.semantic_version)
                major, minor, patch = map(int, latest.semantic_version.split('.'))
                version = f"{major}.{minor}.{patch + 1}"
            else:
                version = "0.1.0"

            # Generate filename and write to disk
            filename = self._generate_filename(name, version, content_hash)
            target_dir = BOOTSTRAP_DIR if is_bootstrap else GENERATED_DIR
            file_path = target_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(code)

            # Create artifact record
            tool = ToolArtifact(
                name=name,
                semantic_version=version,
                file_path=str(file_path.relative_to(target_dir.parent)),
                content_hash=content_hash,
                code_content=code,
                args_schema=args_schema or {},
                permissions=permissions or [Permission.CALC_ONLY.value],
                status=ToolStatus.PROVISIONAL,
                test_cases=test_cases or []
            )

            session.add(tool)
            session.commit()
            session.refresh(tool)

            return tool

    def get_by_name(self, name: str) -> Optional[ToolArtifact]:
        """Get the latest version of a tool by name."""
        with Session(self.engine) as session:
            tools = session.exec(
                select(ToolArtifact).where(ToolArtifact.name == name)
            ).all()

            if not tools:
                return None

            # Return the latest version
            return max(tools, key=lambda t: t.semantic_version)

    def get_by_hash(self, content_hash: str) -> Optional[ToolArtifact]:
        """Get tool by content hash (for deduplication)."""
        with Session(self.engine) as session:
            return session.exec(
                select(ToolArtifact).where(ToolArtifact.content_hash == content_hash)
            ).first()

    def get_by_id(self, tool_id: int) -> Optional[ToolArtifact]:
        """Get tool by ID."""
        with Session(self.engine) as session:
            return session.get(ToolArtifact, tool_id)

    def list_tools(self, status: ToolStatus = None) -> List[ToolArtifact]:
        """List all tools, optionally filtered by status."""
        with Session(self.engine) as session:
            query = select(ToolArtifact)
            if status:
                query = query.where(ToolArtifact.status == status)
            return list(session.exec(query).all())

    def update_status(self, tool_id: int, status: ToolStatus) -> Optional[ToolArtifact]:
        """Update tool status."""
        with Session(self.engine) as session:
            tool = session.get(ToolArtifact, tool_id)
            if tool:
                tool.status = status
                session.add(tool)
                session.commit()
                session.refresh(tool)
            return tool

    def search_similar(self, query: str, top_k: int = 5) -> List[ToolArtifact]:
        """
        Semantic similarity search (stub for Phase 1a).

        In Phase 1b, this will use vector embeddings (ChromaDB).
        For now, returns empty list.
        """
        return []


if __name__ == "__main__":
    # Test the registry
    from src.core.models import init_db

    print("Initializing database...")
    init_db()

    registry = ToolRegistry()

    # Test registration
    test_code = '''
import pandas as pd

def calc_ma(prices: list, window: int = 5) -> float:
    """Calculate simple moving average."""
    return float(pd.Series(prices).rolling(window).mean().iloc[-1])

if __name__ == "__main__":
    assert calc_ma([1, 2, 3, 4, 5], 3) == 4.0
    print("Test passed!")
'''

    print("Registering tool...")
    tool = registry.register(
        name="calc_ma",
        code=test_code,
        args_schema={"prices": "list", "window": "int"},
        permissions=[Permission.CALC_ONLY.value]
    )
    print(f"Registered: {tool.name} v{tool.semantic_version} (ID: {tool.id})")

    # Test retrieval
    print("\nRetrieving tool...")
    retrieved = registry.get_by_name("calc_ma")
    print(f"Retrieved: {retrieved.name} v{retrieved.semantic_version}")

    # Test deduplication
    print("\nTesting deduplication...")
    dup = registry.register(name="calc_ma", code=test_code)
    print(f"Same hash returns same ID: {dup.id == tool.id}")

    # List tools
    print("\nListing tools...")
    tools = registry.list_tools()
    for t in tools:
        print(f"  - {t.name} v{t.semantic_version} ({t.status})")
