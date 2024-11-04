import pytest
import aiohttp
from pathlib import Path
from python2rust.utils.server_tester import ServerTester

pytestmark = pytest.mark.asyncio

class TestServerTester:
    @pytest.fixture
    async def tester(self) -> ServerTester:
        tester = ServerTester(
            startup_timeout=5,
            request_timeout=5
        )
        yield tester
        await tester.__aexit__(None, None, None)

    async def test_server_startup(
        self,
        tester: ServerTester,
        temp_dir: Path,
        web_rust_code: str,
        web_toml_content: str
    ):
        """Test server startup detection."""
        # First build the project
        from python2rust.utils.rust_builder import RustBuilder
        builder = RustBuilder(temp_dir)
        await builder.build(web_rust_code, web_toml_content)
        
        success = await tester._wait_for_server()
        assert success

    async def test_image_verification(
        self,
        tester: ServerTester
    ):
        """Test image verification."""
        # Create test image
        from PIL import Image
        import io
        
        # Create image with expected size
        img = Image.new('RGB', tester.expected_image_size, color='white')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        success, error = await tester._verify_image(img_byte_arr)
        assert success
        assert error is None
        
        # Test wrong size
        img = Image.new('RGB', (100, 100), color='white')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        success, error = await tester._verify_image(img_byte_arr)
        assert not success
        assert "size" in str(error).lower()

    async def test_server_cleanup(
        self,
        tester: ServerTester,
        temp_dir: Path,
        web_rust_code: str,
        web_toml_content: str
    ):
        """Test server cleanup on exit."""
        # Start server
        process, log_file = await tester._run_server(temp_dir)
        assert process is not None
        assert log_file is not None
        
        # Clean up
        tester._stop_server()
        
        # Verify process is stopped
        assert tester.process is None
        assert not process.returncode == None  # Process should be terminated

    async def test_full_server_test(
        self,
        tester: ServerTester,
        temp_dir: Path,
        web_rust_code: str,
        web_toml_content: str
    ):
        """Test complete server testing process."""
        # First build the project
        from python2rust.utils.rust_builder import RustBuilder
        builder = RustBuilder(temp_dir)
        await builder.build(web_rust_code, web_toml_content)
        
        success, error, results = await tester.test_server(temp_dir)
        
        assert success
        assert error is None
        assert "get" in results
        assert "post" in results
        assert results["get"]["status"] == 200
        assert results["post"]["status"] == 200

    @pytest.mark.parametrize("port", [8081, 8082])  # Test different ports
    async def test_custom_port(
        self,
        port: int,
        temp_dir: Path
    ):
        """Test server on different ports."""
        tester = ServerTester(port=port)
        
        # Modify web code to use custom port
        web_code = f"""
        use actix_web::{{web, App, HttpResponse, HttpServer}};
        
        async fn hello() -> HttpResponse {{
            HttpResponse::Ok().body("Hello!")
        }}
        
        #[actix_web::main]
        async fn main() -> std::io::Result<()> {{
            HttpServer::new(|| {{
                App::new().route("/", web::get().to(hello))
            }})
            .bind("127.0.0.1:{port}")?
            .run()
            .await
        }}
        """
        
        # Build and test
        from python2rust.utils.rust_builder import RustBuilder
        builder = RustBuilder(temp_dir)
        await builder.build(web_code, """
        [package]
        name = "test_server"
        version = "0.1.0"
        edition = "2021"
        
        [dependencies]
        actix-web = "4.0"
        tokio = { version = "1.0", features = ["full"] }
        """)
        
        success, error, results = await tester.test_server(temp_dir)
        assert success
        assert error is None