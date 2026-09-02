"""Compile the FaceVerify Solidity contract to ABI + bytecode JSON."""

import json
import subprocess
import sys
from pathlib import Path

CONTRACT_PATH = Path(__file__).parent / "contracts" / "FaceVerify.sol"
OUTPUT_PATH = Path(__file__).parent / "contracts" / "FaceVerify.json"


def compile_with_solcx():
    """Compile using py-solc-x (pip install py-solc-x)."""
    try:
        from solcx import compile_standard, install_solc
    except ImportError:
        print("py-solc-x not installed. Install with: pip install py-solc-x")
        return False

    # Install solc 0.8.20 if not present
    install_solc("0.8.20")

    source = CONTRACT_PATH.read_text()

    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": {"FaceVerify.sol": {"content": source}},
            "settings": {
                "outputSelection": {
                    "*": {"*": ["abi", "evm.bytecode"]}
                }
            },
        },
        solc_version="0.8.20",
    )

    contract = compiled["contracts"]["FaceVerify.sol"]["FaceVerify"]
    abi = contract["abi"]
    bytecode = contract["evm"]["bytecode"]["object"]

    OUTPUT_PATH.write_text(json.dumps({"abi": abi, "bytecode": bytecode}, indent=2))
    print(f"Compiled contract written to {OUTPUT_PATH}")
    return True


def compile_with_solc_binary():
    """Fallback: use solc binary if available."""
    try:
        result = subprocess.run(
            ["solc", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

    # Use standard JSON input
    std_input = {
        "language": "Solidity",
        "sources": {"FaceVerify.sol": {"content": CONTRACT_PATH.read_text()}},
        "settings": {
            "outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}}
        },
    }

    proc = subprocess.run(
        ["solc", "--standard-json"],
        input=json.dumps(std_input),
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        print(f"solc error:\n{proc.stderr}")
        return False

    compiled = json.loads(proc.stdout)
    contract = compiled["contracts"]["FaceVerify.sol"]["FaceVerify"]
    abi = contract["abi"]
    bytecode = contract["evm"]["bytecode"]["object"]

    OUTPUT_PATH.write_text(json.dumps({"abi": abi, "bytecode": bytecode}, indent=2))
    print(f"Compiled contract written to {OUTPUT_PATH}")
    return True


def compile_with_remix_instructions():
    """Print instructions for manual compilation."""
    print("=" * 60)
    print("Automatic compilation failed. Manual steps:")
    print("=" * 60)
    print("1. Go to https://remix.ethereum.org")
    print("2. Create a new file 'FaceVerify.sol' and paste the contract code")
    print("3. Compile with Solidity 0.8.20")
    print("4. In the 'Compilation Details' tab, copy 'ABI' and 'bytecode'")
    print(f"5. Save as JSON to: {OUTPUT_PATH}")
    print('   Format: {"abi": [...], "bytecode": "0x..."}')
    print("=" * 60)
    return False


if __name__ == "__main__":
    print("Compiling FaceVerify.sol...")
    if not compile_with_solcx():
        if not compile_with_solc_binary():
            compile_with_remix_instructions()
            sys.exit(1)
    print("Done.")
