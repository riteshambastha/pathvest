# LEAN Docker Setup Guide

## ✅ What's Ready

All code and configuration files are prepared and ready to go:

1. **LEAN Engine Wrapper** (`backend/app/services/lean_engine.py`)
   - Full integration with PathVest
   - Configuration translation
   - Results parsing

2. **Base Strategy Class** (`backend/lean/algorithms/pathvest_base_strategy.py`)
   - Event-driven architecture ✅
   - Fractional shares support ✅
   - Transaction costs (commission + slippage) ✅
   - Position management ✅

3. **Configuration Files** (`backend/lean/config/`)
   - `config.json` - Local configuration
   - `lean-config.json` - Docker configuration
   - Full documentation

4. **Test Suite** (`backend/lean/tests/`)
   - Basic backtest test
   - Fractional shares verification
   - Ready to run once Docker is installed

5. **Verification Script** (`backend/lean/verify_docker.py`)
   - Checks Docker installation
   - Pulls LEAN image
   - Tests container functionality

---

## ⏸️ Waiting For: Docker Installation

### Current Status
The Docker DMG file has been opened. Please complete the installation:

### Installation Steps

1. **Install Docker Desktop**
   - Look for the opened DMG window
   - Drag `Docker.app` to the `Applications` folder
   - Close the DMG

2. **Start Docker Desktop**
   - Open `Docker.app` from Applications (or use Spotlight: Cmd+Space, type "Docker")
   - Accept any terms and conditions
   - Docker will start initializing (this takes 1-2 minutes)

3. **Wait for Docker to be Ready**
   - Look for the whale icon 🐳 in your menu bar (top right)
   - Wait until the whale stops animating (means Docker is fully started)
   - You might see a notification: "Docker Desktop is running"

4. **Verify Installation**
   - Open a new terminal window
   - Run: `docker --version`
   - You should see something like: `Docker version 24.0.x, build xxxxx`

---

## 🚀 Next Steps (After Docker is Running)

Once Docker is installed and running, let me know and I'll:

### Phase 2: LEAN Core Integration (Immediate)

1. **Verify Docker Setup**
   ```bash
   cd /Users/riteshambastha/projects/pathvest/backend
   source venv-lean/bin/activate
   python lean/verify_docker.py
   ```

2. **Pull LEAN Docker Image**
   ```bash
   docker pull quantconnect/lean:latest
   ```
   This downloads the LEAN engine (takes 5-10 minutes on first run)

3. **Run Basic Tests**
   ```bash
   python lean/tests/test_basic_backtest.py
   ```
   This will test:
   - ✅ Basic backtest execution
   - ✅ Fractional shares support (FR-3.1.D.4)
   - ✅ Transaction costs (FR-3.1.C.7)
   - ✅ Event-driven processing (FR-3.1.D.1)

4. **Verify Results**
   - Check that backtest completes successfully
   - Verify fractional shares are working
   - Confirm transaction costs are applied

---

## 📋 Full Integration Phases

```
✅ Phase 1: Environment Setup (95% complete, waiting for Docker)
⏸️ Phase 2: LEAN Core Integration (code ready, waiting to test)
⏸️ Phase 3: Custom Data Sources (SEC 13F integration)
⏸️ Phase 4: Strategy Translation (Config → LEAN code)
⏸️ Phase 5: Results Integration (LEAN → PathVest format)
⏸️ Phase 6: Testing & Validation (End-to-end tests)
```

**Estimated Time After Docker Install**: 2-3 hours for Phase 2, then ~3-4 days for remaining phases

---

## 🐳 Docker Troubleshooting

### Docker Desktop won't start
- Make sure you have macOS 10.15 or later
- Check Activity Monitor for any Docker processes and quit them
- Try restarting your Mac

### "Cannot connect to Docker daemon"
- Docker Desktop needs to be running (whale icon in menu bar)
- Wait 2-3 minutes after starting Docker Desktop
- Try running: `docker ps` to test connection

### Docker image pull is slow
- This is normal on first run (1-2 GB download)
- Ensure you have stable internet connection
- The image is cached after first download

### Permission errors
- Docker Desktop should handle permissions automatically
- If issues persist, try: `sudo docker ps` to check if it's a permission issue

---

## 📞 Need Help?

If you encounter any issues:
1. Check the whale icon 🐳 in menu bar - is it animated (starting) or static (ready)?
2. Run: `docker ps` - does it show a table (even if empty)?
3. Check Docker Desktop settings → Resources - ensure VM is allocated enough resources
4. Let me know the exact error message

---

## 🎯 Success Criteria

You'll know Docker is ready when:
- ✅ Whale icon is in menu bar and not animated
- ✅ `docker --version` shows version number
- ✅ `docker ps` runs without errors
- ✅ `docker run hello-world` completes successfully

Once all are ✅, let me know and we'll continue immediately! 🚀

