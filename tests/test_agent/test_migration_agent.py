import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from python2rust.agent.migration_agent import MigrationAgent
from python2rust.config.settings import Settings

pytestmark = pytest.mark.asyncio

class TestMigrationAgent:
    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Create test settings."""
        settings = Settings()
        settings.output_dir = Path("test_output")
        settings.debug_dir = Path("test_output/debug")
        settings.max_attempts = 2
        settings.max_fixes_per_attempt = 2
        return settings

    @pytest.fixture
    def sample_python_code(self) -> str:
        """Sample Python web server code."""
        return """
        from flask import Flask, render_template
        import matplotlib.pyplot as plt
        import numpy as np

        app = Flask(__name__)

        @app.route('/', methods=['GET', 'POST'])
        def index():
            if request.method == 'POST':
                # Generate mandelbrot
                x = np.linspace(-2, 1, 2000)
                y = np.linspace(-1.5, 1.5, 2000)
                c = x[:, np.newaxis] + 1j * y
                z = c
                divtime = 20 + np.zeros(z.shape, dtype=int)
                for i in range(20):
                    z = z**2 + c
                    diverge = z*np.conj(z) > 2**2
                    div_now = diverge & (divtime == 20 + np.zeros(z.shape, dtype=int))
                    divtime[div_now] = i
                plt.figure(figsize=(10, 10))
                plt.imshow(divtime, cmap='magma')
                plt.colorbar()
                img = io.BytesIO()
                plt.savefig(img, format='png')
                img.seek(0)
                return send_file(img, mimetype='image/png')
            return render_template('index.html')

        if __name__ == '__main__':
            app.run(port=8080)
        """

    @pytest.fixture
    def sample_rust_response(self) -> str:
        """Sample LLM response with Rust code."""
        return """
Here's the Rust implementation:

```rust
use actix_web::{web, App, HttpResponse, HttpServer};
use image::{ImageBuffer, Rgb};
use plotters::prelude::*;

async fn index() -> HttpResponse {
    // Implementation...
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    HttpServer::new(|| {
        App::new().route("/", web::get().to(index))
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}
```

```toml
[package]
name = "mandelbrot_server"
version = "0.1.0"
edition = "2021"

[dependencies]
actix-web = "4.0"
image = "0.24"
plotters = "0.3"
```
"""

    @pytest.fixture
    def mock_llm_responses(self, sample_rust_response: str) -> dict:
        """Mock LLM responses for different steps."""
        return {
            "analysis": {
                "core_patterns": ["Mandelbrot set calculation", "Image generation"],
                "required_types": ["Complex numbers", "2D arrays"],
                "output_formats": ["PNG image", "HTML template"]
            },
            "generation": sample_rust_response,
            "verification": {
                "matches": True,
                "critical_differences": []
            }
        }

    @pytest.fixture
    async def agent(
        self,
        temp_dir: Path,
        mock_settings: Settings,
        mock_llm_responses: dict
    ) -> MigrationAgent:
        """Create test agent with mocked LLMs."""
        with patch("langchain.chat_models.ChatAnthropic") as mock_claude, \
             patch("langchain.llms.HuggingFaceEndpoint") as mock_hf:
            
            # Mock Claude responses
            mock_claude_instance = AsyncMock()
            mock_claude_instance.agenerate.side_effect = [
                [MagicMock(text=str(mock_llm_responses["analysis"]))],
                [MagicMock(text=str(mock_llm_responses["verification"]))]
            ]
            mock_claude.return_value = mock_claude_instance
            
            # Mock HuggingFace responses
            mock_hf_instance = AsyncMock()
            mock_hf_instance.agenerate.side_effect = [
                [MagicMock(text=mock_llm_responses["generation"])]
            ]
            mock_hf.return_value = mock_hf_instance
            
            # Create agent
            agent = MigrationAgent(
                claude_token="test_token",
                hf_token="test_token",
                output_dir=temp_dir,
                settings=mock_settings
            )
            
            yield agent

    async def test_successful_migration(
        self,
        agent: MigrationAgent,
        sample_python_code: str
    ):
        """Test successful migration flow."""
        success, rust_code, toml_content = await agent.migrate(sample_python_code)
        
        assert success
        assert rust_code is not None
        assert toml_content is not None
        assert "actix-web" in toml_content
        
        # Check debug artifacts
        assert (agent.settings.debug_dir / "attempt_0").exists()
        assert (agent.settings.debug_dir / "attempt_0" / "SUCCESS").exists()

    async def test_failed_verification_with_fix(
        self,
        agent: MigrationAgent,
        sample_python_code: str,
        mock_llm_responses: dict
    ):
        """Test migration with initial verification failure but successful fix."""
        # Modify mock responses for failed then successful verification
        mock_llm_responses["verification"] = [
            {
                "matches": False,
                "critical_differences": ["Image size mismatch"]
            },
            {
                "matches": True,
                "critical_differences": []
            }
        ]
        
        # Add fix response
        mock_llm_responses["fix"] = mock_llm_responses["generation"]
        
        with patch.object(agent.chains["verification"], "verify") as mock_verify:
            mock_verify.side_effect = [
                mock_llm_responses["verification"][0],
                mock_llm_responses["verification"][1]
            ]
            
            success, rust_code, toml_content = await agent.migrate(sample_python_code)
            
            assert success
            assert rust_code is not None
            assert mock_verify.call_count == 2

    async def test_build_failure(
        self,
        agent: MigrationAgent,
        sample_python_code: str
    ):
        """Test handling of Rust build failures."""
        with patch("python2rust.utils.rust_builder.RustBuilder.build") as mock_build:
            mock_build.return_value = (False, "Compilation error", {})
            
            success, rust_code, toml_content = await agent.migrate(sample_python_code)
            
            assert not success
            assert mock_build.call_count == agent.settings.max_attempts

    @pytest.mark.parametrize("error_type", ["analysis", "generation", "verification"])
    async def test_llm_errors(
        self,
        agent: MigrationAgent,
        sample_python_code: str,
        error_type: str
    ):
        """Test handling of LLM errors in different stages."""
        with patch.object(agent.chains[error_type], error_type) as mock_step:
            mock_step.side_effect = Exception(f"LLM {error_type} failed")
            
            success, rust_code, toml_content = await agent.migrate(sample_python_code)
            
            assert not success
            assert mock_step.call_count >= 1

    async def test_server_test_failure(
        self,
        agent: MigrationAgent,
        sample_python_code: str
    ):
        """Test handling of server test failures."""
        with patch("python2rust.utils.server_tester.ServerTester.test_server") as mock_test:
            mock_test.return_value = (False, "Server test failed", {})
            
            success, rust_code, toml_content = await agent.migrate(sample_python_code)
            
            assert not success
            assert mock_test.call_count >= 1

    async def test_debug_artifacts(
        self,
        agent: MigrationAgent,
        sample_python_code: str
    ):
        """Test creation and content of debug artifacts."""
        await agent.migrate(sample_python_code)
        
        debug_dir = agent.settings.debug_dir
        assert debug_dir.exists()
        
        # Check attempt directory
        attempt_dir = debug_dir / "attempt_0"
        assert attempt_dir.exists()
        
        # Check debug files
        assert (attempt_dir / "config" / "llm_config.json").exists()
        assert (attempt_dir / "src" / "main.rs").exists()
        assert (attempt_dir / "Cargo.toml").exists()
        
        # Check logs
        assert (attempt_dir / "logs").exists()
        
        # Check summary
        assert (debug_dir / "summary.json").exists()
        
        # Verify summary content
        import json
        summary = json.loads((debug_dir / "summary.json").read_text())
        assert "attempts" in summary
        assert "total_attempts" in summary
        assert len(summary["attempts"]) > 0

    async def test_token_usage_tracking(
        self,
        agent: MigrationAgent,
        sample_python_code: str
    ):
        """Test token usage tracking in debug artifacts."""
        await agent.migrate(sample_python_code)
        
        # Check LLM config files
        attempt_dir = agent.settings.debug_dir / "attempt_0"
        llm_config = json.loads(
            (attempt_dir / "config" / "llm_config.json").read_text()
        )
        
        # Verify token usage tracking
        for step in ["analysis", "generation", "verification"]:
            assert step in llm_config
            assert "token_usage" in llm_config[step]