"""
Main entry point for python2rust migration tool.
"""
import asyncio
import argparse
from pathlib import Path
import sys
from typing import Optional, Dict

from .agent.migration_agent import MigrationAgent
from .config.settings import Settings, LLMChoice
from .utils.logging import setup_logger

logger = setup_logger()

def check_token_files() -> Dict[str, Optional[str]]:
    """Check and load token files."""
    project_root = Path(__file__).parent.parent.parent
    tokens = {}
    
    # Check Claude token (required)
    claude_token_path = project_root / ".claude_token"
    try:
        tokens["claude"] = claude_token_path.read_text().strip()
        if not tokens["claude"]:
            raise ValueError("Claude token file is empty")
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Claude token error: {str(e)}")
        print(f"""
Error: Claude API token not found or invalid.
Please create {claude_token_path} with your Claude API key from https://console.anthropic.com/
""")
        sys.exit(1)
    
    # Check HuggingFace token (optional)
    hf_token_path = project_root / ".hf_token"
    try:
        tokens["hf"] = hf_token_path.read_text().strip()
        if tokens["hf"]:
            logger.info("HuggingFace token found - CodeLlama and StarCoder available")
        else:
            logger.warning("HuggingFace token file is empty")
            tokens["hf"] = None
    except FileNotFoundError:
        logger.info("No HuggingFace token found - will use Claude for all operations")
        tokens["hf"] = None
    
    return tokens

def validate_python_file(file_path: Path) -> str:
    """Validate and read Python input file."""
    try:
        if not file_path.exists():
            raise FileNotFoundError(f"Python file not found: {file_path}")
        
        if file_path.suffix != '.py':
            raise ValueError(f"File must have .py extension: {file_path}")
        
        content = file_path.read_text()
        if not content.strip():
            raise ValueError(f"Python file is empty: {file_path}")
        
        return content
        
    except Exception as e:
        logger.error(f"Input file error: {str(e)}")
        print(f"Error: {str(e)}")
        sys.exit(1)

async def migrate_code(
    python_file: Path,
    output_dir: Path,
    tokens: Dict[str, Optional[str]]
) -> bool:
    """Execute the migration process."""
    try:
        # Read and validate Python code
        python_code = validate_python_file(python_file)
        
        # Configure settings based on available tokens
        settings = Settings(
            output_dir=output_dir,
            llm_steps={
                "analysis": LLMChoice.CLAUDE,
                "generation": LLMChoice.CODELLAMA if tokens["hf"] else LLMChoice.CLAUDE,
                "verification": LLMChoice.CLAUDE,
                "fixes": LLMChoice.CODELLAMA if tokens["hf"] else LLMChoice.CLAUDE
            }
        )
        
        # Log configuration
        logger.info("Migration configuration:")
        logger.info(f"- Input file: {python_file}")
        logger.info(f"- Output directory: {output_dir}")
        logger.info(f"- Analysis: {settings.llm_steps.analysis}")
        logger.info(f"- Generation: {settings.llm_steps.generation}")
        logger.info(f"- Verification: {settings.llm_steps.verification}")
        logger.info(f"- Fixes: {settings.llm_steps.fixes}")
        
        # Initialize and run migration agent
        async with MigrationAgent(
            claude_token=tokens["claude"],
            hf_token=tokens["hf"],
            output_dir=output_dir,
            settings=settings
        ) as agent:
            success, rust_code, toml_content = await agent.migrate(python_code)
            
            if success:
                logger.info("Migration successful!")
                
                # Show output locations
                print("\nMigration successful!")
                print(f"Generated files in: {output_dir}")
                print(f"Debug information in: {output_dir}/debug")
                print(f"Logs in: {Path('logs')}")
                
                return True
            else:
                logger.error("Migration failed!")
                print("\nMigration failed - check logs for details")
                return False
                
    except Exception as e:
        logger.exception(f"Migration error: {str(e)}")
        return False

def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate Python code to Rust",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--python-file",
        type=Path,
        required=True,
        help="Path to Python source file"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("generated"),
        help="Output directory for generated code"
    )
    
    args = parser.parse_args()
    
    try:
        # Check token files
        tokens = check_token_files()
        
        # Create output directory
        args.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Run migration
        success = asyncio.run(migrate_code(
            python_file=args.python_file,
            output_dir=args.output_dir,
            tokens=tokens
        ))
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\nMigration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()