import pytest
from pathlib import Path
from python2rust.utils.rust_builder import RustBuilder

pytestmark = pytest.mark.asyncio

class TestRustBuilder:
    @pytest.fixture
    async def builder(self, temp_dir: Path) -> RustBuilder:
        return RustBuilder(temp_dir)

    async def test_prepare_project(
        self,
        builder: RustBuilder,
        simple_rust_code: str,
        simple_toml_content: str
    ):
        """Test project preparation."""
        project_dir = builder.prepare_project(simple_rust_code, simple_toml_content)
        
        # Check directory structure
        assert (project_dir / "src").exists()
        assert (project_dir / "src" / "main.rs").exists()
        assert (project_dir / "Cargo.toml").exists()
        
        # Check file contents
        assert (project_dir / "src" / "main.rs").read_text() == simple_rust_code
        assert (project_dir / "Cargo.toml").read_text() == simple_toml_content

    async def test_build_success(
        self,
        builder: RustBuilder,
        simple_rust_code: str,
        simple_toml_content: str
    ):
        """Test successful build."""
        success, error, info = await builder.build(simple_rust_code, simple_toml_content)
        
        assert success
        assert error is None
        assert "duration" in info
        assert "log_file" in info
        assert Path(info["log_file"]).exists()

    async def test_build_failure(
        self,
        builder: RustBuilder
    ):
        """Test build failure with invalid code."""
        invalid_code = "this is not valid rust code"
        invalid_toml = "[package]\nname = 'test'"
        
        success, error, info = await builder.build(invalid_code, invalid_toml)
        
        assert not success
        assert error is not None
        assert "error" in str(error).lower()
        assert Path(info["log_file"]).exists()

    async def test_check(
        self,
        builder: RustBuilder,
        simple_rust_code: str,
        simple_toml_content: str
    ):
        """Test cargo check."""
        success, error, info = await builder.check(simple_rust_code, simple_toml_content)
        
        assert success
        assert error is None
        assert "output_dir" in info

    async def test_clippy(
        self,
        builder: RustBuilder,
        simple_rust_code: str,
        simple_toml_content: str
    ):
        """Test clippy lints."""
        success, error, info = await builder.clippy(simple_rust_code, simple_toml_content)
        
        assert success
        assert error is None
        assert "output" in info

    async def test_build_timeout(
        self,
        temp_dir: Path
    ):
        """Test build timeout handling."""
        # Create builder with very short timeout
        builder = RustBuilder(temp_dir, build_timeout=1)
        
        # Create infinite loop Rust code
        infinite_code = """
        fn main() {
            loop {}
        }
        """
        
        success, error, info = await builder.build(infinite_code, "[package]\nname='test'\nversion='0.1.0'\nedition='2021'")
        
        assert not success
        assert "timeout" in str(error).lower()