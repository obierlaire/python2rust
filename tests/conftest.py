import pytest
import tempfile
from pathlib import Path
from typing import Generator, AsyncGenerator

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)

@pytest.fixture
def simple_rust_code() -> str:
    """Sample Rust code for testing."""
    return """
fn main() {
    println!("Hello, world!");
}
"""

@pytest.fixture
def simple_toml_content() -> str:
    """Sample Cargo.toml for testing."""
    return """
[package]
name = "test_project"
version = "0.1.0"
edition = "2021"

[dependencies]
"""

@pytest.fixture
def web_rust_code() -> str:
    """Sample Rust web server code for testing."""
    return """
use actix_web::{web, App, HttpResponse, HttpServer};

async fn hello() -> HttpResponse {
    HttpResponse::Ok().body("Hello!")
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    HttpServer::new(|| {
        App::new().route("/", web::get().to(hello))
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}
"""

@pytest.fixture
def web_toml_content() -> str:
    """Sample Cargo.toml for web server."""
    return """
[package]
name = "test_server"
version = "0.1.0"
edition = "2021"

[dependencies]
actix-web = "4.0"
tokio = { version = "1.0", features = ["full"] }
"""