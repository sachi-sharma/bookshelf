# Fix Node.js Compatibility - Step by Step

Your Homebrew Node.js (24.3.0) requires macOS 13.5+, but you're on macOS 13.2.1. Follow these steps:

## Step 1: Close and Reopen Your Terminal

This ensures the `.zshrc` changes are loaded.

## Step 2: Load nvm and Install Node.js 20

Run these commands in your terminal:

```bash
# Load nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Install Node.js 20 (compatible with your macOS)
nvm install 20

# Use Node.js 20
nvm use 20

# Set as default
nvm alias default 20
```

## Step 3: Verify Installation

```bash
# Check Node.js version (should show v20.x.x)
node --version

# Check which node is being used (should show ~/.nvm/...)
which node

# Check npm
npm --version
```

## Step 4: If Still Getting Errors

If `node --version` still shows the Homebrew error, manually remove Homebrew's node from PATH:

```bash
# Temporarily remove Homebrew's node
export PATH=$(echo $PATH | tr ':' '\n' | grep -v '/opt/homebrew/bin' | tr '\n' ':' | sed 's/:$//')

# Then try again
node --version
```

## Step 5: Make It Permanent

The `.zshrc` has been updated, but you may need to manually ensure nvm's node comes first. 

Open `~/.zshrc` and make sure these lines are at the END of the file:

```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Ensure nvm's node is in PATH before Homebrew
if command -v nvm &> /dev/null; then
    NODE_VERSION=$(nvm version 2>/dev/null)
    if [ -n "$NODE_VERSION" ] && [ "$NODE_VERSION" != "N/A" ]; then
        export PATH="$NVM_DIR/versions/node/$NODE_VERSION/bin:$PATH"
    fi
fi
```

Then reload:
```bash
source ~/.zshrc
```

## Alternative: Use a Different Shell Session

If the above doesn't work, try opening a completely new terminal window (not just reloading), as the Homebrew node might be cached.

## Once Node.js Works

You can proceed with frontend setup:

```bash
cd frontend
npm install
npm run dev
```

