# Face Identification & Blockchain Verification Pipeline

HH Goa 2026 — Task 3

**Face scan → Web/social media search → Blockchain upload & verification**

## What It Does

This project implements an end-to-end pipeline that:

1. **Detects and encodes a face** from an input image using `deepface` (VGG-Face model)
2. **Searches the web** for matching social media posts using SerpApi's Google Lens API (reverse image search)
3. **Uploads a tamper-evident fingerprint** of the discovered post to the Sepolia Ethereum testnet
4. **Re-verifies the data** against the on-chain record to prove integrity

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Face Image │────▶│  Google Lens API  │────▶│  Sepolia Testnet │
│  (input)    │     │  (visual search)  │     │  (hash storage)  │
└─────────────┘     └──────────────────┘     └─────────────────┘
       │                     │                         │
       ▼                     ▼                         ▼
  128-d encoding      Social media post URL      On-chain verification
```

## Tech Stack

| Component | Tool | Purpose |
|-----------|------|---------|
| Face Detection | `deepface` (VGG-Face) | Detect + encode faces |
| Web Search | SerpApi Google Lens API | Reverse image search |
| Blockchain | Solidity + web3.py | Hash storage on Sepolia |
| Network | Sepolia Testnet | Ethereum test chain |

## Setup

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/face-verify.git
cd face-verify
pip install -r requirements.txt
```

### 2. Get API keys

**SerpApi** (free tier: 250 searches/month):
1. Sign up at https://serpapi.com
2. Copy your API key from the dashboard

**Sepolia test ETH** (free):
1. Create a MetaMask wallet (or use an existing one)
2. Switch to Sepolia network
3. Get free test ETH from a faucet:
   - https://sepoliafaucet.com
   - https://www.alchemy.com/faucets/ethereum-sepolia
4. Export your private key (Settings → Advanced → Account Details → Export Private Key)

**Alchemy/Infura RPC URL** (free):
1. Sign up at https://alchemy.com or https://infura.io
2. Create a Sepolia app
3. Copy the HTTPS RPC URL

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:
```
SERPAPI_KEY=your_serpapi_key
PRIVATE_KEY=your_wallet_private_key
SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/your_key
CONTRACT_ADDRESS=  # fill after deploying
```

### 4. Compile and deploy the smart contract

```bash
# Option A: If you have solc installed
pip install py-solc-x
python compile_contract.py

# Option B: Use Remix IDE
# 1. Go to https://remix.ethereum.org
# 2. Paste contracts/FaceVerify.sol
# 3. Compile with Solidity 0.8.20
# 4. Copy ABI + bytecode → save to contracts/FaceVerify.json
```

Deploy to Sepolia:
```bash
python main.py --deploy
```

Update `CONTRACT_ADDRESS` in `.env` with the output.

## Usage

### Run the full pipeline

```bash
python main.py --image test_faces/sample.jpg
```

This will:
1. Detect the face and generate a 128-d encoding
2. Upload the image to Google Lens via SerpApi
3. Find matching social media posts
4. Compute a SHA-256 fingerprint of the discovered post
5. Store the fingerprint on Sepolia testnet
6. Re-verify the hash against the on-chain record

### Other commands

```bash
# Deploy the contract
python main.py --deploy

# Verify a specific hash
python main.py --verify <sha256_hex_digest>

# Check how many hashes are stored
python main.py --count

# Use exact match search instead of visual matches
python main.py --image photo.jpg --search-type exact_matches
```

## Output

Results are saved to `outputs/result_YYYYMMDD_HHMMSS.json`:

```json
{
  "timestamp": "2026-09-01T12:00:00+00:00",
  "input_image": "test_faces/sample.jpg",
  "steps": {
    "face_detection": { "status": "success", "encoding_hash": "..." },
    "web_search": {
      "status": "success",
      "discovered_post": {
        "title": "John at the beach",
        "link": "https://instagram.com/p/ABC123",
        "source": "Instagram"
      },
      "post_fingerprint": "a1b2c3..."
    },
    "blockchain": { "status": "success", "tx_hash": "0x..." },
    "on_chain_verification": { "status": "verified" }
  }
}
```

## Project Structure

```
face-verify/
├── main.py               # Pipeline orchestrator (CLI)
├── face_detector.py      # Face detection + encoding
├── web_search.py         # SerpApi Google Lens integration
├── blockchain.py         # web3.py + Sepolia interaction
├── compile_contract.py   # Solidity compiler script
├── contracts/
│   ├── FaceVerify.sol    # Smart contract source
│   └── FaceVerify.json   # Compiled ABI + bytecode
├── test_faces/           # Sample face images
├── outputs/              # Pipeline results
├── requirements.txt
├── .env.example
└── README.md
```

## Smart Contract: FaceVerify

The contract stores SHA-256 fingerprints of discovered social media posts.

**Functions:**
- `verifyPost(hash, url, title, source)` — store a new fingerprint
- `isVerified(hash)` — check if a hash exists
- `getVerification(hash)` — retrieve the full record
- `getStoredCount()` — total hashes stored

**Network:** Sepolia Testnet (Chain ID: 11155111)

## Known Limitations

1. **SerpApi rate limit:** Free tier allows 250 searches/month
2. **Face detection:** Works best with clear, front-facing photos; may fail with extreme angles or heavy occlusion
3. **Social media detection:** Based on URL pattern matching — some platforms may be missed
4. **Sepolia gas:** Contract deployment costs ~0.001 ETH (free from faucets)
5. **Image upload size:** SerpApi limits uploads to 500KB (JPG/PNG/WebP)
6. **First run:** deepface will download the VGG-Face model (~500MB) on first use

## License

MIT
