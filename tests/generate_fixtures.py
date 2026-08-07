"""Generate test fixture STL models for end-to-end testing."""
import trimesh
from pathlib import Path


def create_test_models() -> None:
    fixtures_dir = Path(__file__).parent / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)

    healthy = trimesh.creation.icosphere(subdivisions=2, radius=10)
    healthy.export(fixtures_dir / "healthy.stl")

    thin_wall = trimesh.creation.box(extents=[10, 10, 0.3])
    thin_wall.export(fixtures_dir / "thin_wall.stl")

    overhang = trimesh.creation.icosphere(subdivisions=3, radius=10)
    overhang.export(fixtures_dir / "overhang.stl")


if __name__ == "__main__":
    create_test_models()
