#!/bin/bash
# HackathonHero - MacOS PATH Fix Helper
# Run this if the main setup script fails due to PATH issues

echo "🔧 HackathonHero PATH Fix Helper"
echo "================================"

# Detect architecture for Homebrew paths
if [[ $(uname -m) == 'arm64' ]]; then
    BREW_PREFIX="/opt/homebrew"
else
    BREW_PREFIX="/usr/local"
fi

echo "Detected architecture: $(uname -m)"
echo "Brew prefix: $BREW_PREFIX"

# Add paths to current session
export PATH="${BREW_PREFIX}/opt/python@3.11/bin:$PATH"
export PATH="${BREW_PREFIX}/opt/node@22/bin:$PATH"
export PATH="${BREW_PREFIX}/bin:$PATH"

echo ""
echo "Updated PATH for current session:"
echo "$PATH"
echo ""

# Check if tools are now available
echo "🔍 Checking tools availability:"
echo "  Python3: $(which python3 2>/dev/null || echo 'not found')"
echo "  Node.js: $(which node 2>/dev/null || echo 'not found')"
echo "  npm: $(which npm 2>/dev/null || echo 'not found')"
echo ""

# Add to shell profile if not already there
ZSHRC="$HOME/.zshrc"
echo "📝 Updating shell profile ($ZSHRC):"

if ! grep -q "export PATH=\"${BREW_PREFIX}/bin:\$PATH\"" "$ZSHRC" 2>/dev/null; then
    echo "export PATH=\"${BREW_PREFIX}/bin:\$PATH\"" >> "$ZSHRC"
    echo "  ✅ Added Homebrew to PATH"
else
    echo "  ⏭️  Homebrew already in PATH"
fi

if ! grep -q "export PATH=\"${BREW_PREFIX}/opt/python@3.11/bin:\$PATH\"" "$ZSHRC" 2>/dev/null; then
    echo "export PATH=\"${BREW_PREFIX}/opt/python@3.11/bin:\$PATH\"" >> "$ZSHRC"
    echo "  ✅ Added Python 3.11 to PATH"
else
    echo "  ⏭️  Python 3.11 already in PATH"
fi

if ! grep -q "export PATH=\"${BREW_PREFIX}/opt/node@22/bin:\$PATH\"" "$ZSHRC" 2>/dev/null; then
    echo "export PATH=\"${BREW_PREFIX}/opt/node@22/bin:\$PATH\"" >> "$ZSHRC"
    echo "  ✅ Added Node.js 22 to PATH"
else
    echo "  ⏭️  Node.js 22 already in PATH"
fi

echo ""
echo "🎉 PATH fix complete!"
echo ""
echo "Next steps:"
echo "  1. Run: source ~/.zshrc"
echo "  2. Or restart your terminal"
echo "  3. Then run the main setup script again"