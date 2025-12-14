#!/bin/bash

###############################################################################
# Quality Wall - Le Petit Prince RAG
#
# Exécute les vérifications de qualité dans l'ordre défini par CLAUDE.md:
# 1. Black (formatage)
# 2. Ruff (linting + fixes)
# 3. Mypy (type checking)
# 4. Pytest (tests)
#
# Usage:
#   ./scripts/quality_wall.sh [--fix] [--skip-tests]
#
# Options:
#   --fix: Applique les corrections automatiques (Black, Ruff)
#   --skip-tests: Skip les tests (pour vérif rapide)
#   --verbose: Mode verbeux
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
FIX_MODE=false
SKIP_TESTS=false
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX_MODE=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--fix] [--skip-tests] [--verbose]"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Banner
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Le Petit Prince RAG - Quality Wall            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if we're in project root
if [ ! -f "CLAUDE.md" ]; then
    echo -e "${RED}❌ Error: Must be run from project root${NC}"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
    source .venv/bin/activate
fi

# Track overall status
WALL_STATUS=0

###############################################################################
# STEP 1: Black (Code Formatting)
###############################################################################

echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 1/4: Black (Code Formatting)${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"

if $FIX_MODE; then
    echo "🎨 Running Black (fixing)..."
    if $VERBOSE; then
        black src/ tests/
    else
        black src/ tests/ --quiet
    fi
    BLACK_STATUS=$?
else
    echo "🎨 Running Black (check only)..."
    if $VERBOSE; then
        black --check src/ tests/
    else
        black --check src/ tests/ --quiet
    fi
    BLACK_STATUS=$?
fi

if [ $BLACK_STATUS -eq 0 ]; then
    echo -e "${GREEN}✅ Black: PASSED${NC}"
else
    echo -e "${RED}❌ Black: FAILED${NC}"
    echo -e "${YELLOW}   Tip: Run with --fix to auto-format${NC}"
    WALL_STATUS=1
fi

###############################################################################
# STEP 2: Ruff (Linting)
###############################################################################

echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 2/4: Ruff (Linting)${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"

if $FIX_MODE; then
    echo "🔍 Running Ruff (with auto-fix)..."
    if $VERBOSE; then
        ruff check --fix src/ tests/
    else
        ruff check --fix src/ tests/ --quiet
    fi
    RUFF_STATUS=$?
else
    echo "🔍 Running Ruff (check only)..."
    if $VERBOSE; then
        ruff check src/ tests/
    else
        ruff check src/ tests/ --quiet
    fi
    RUFF_STATUS=$?
fi

if [ $RUFF_STATUS -eq 0 ]; then
    echo -e "${GREEN}✅ Ruff: PASSED${NC}"
else
    echo -e "${RED}❌ Ruff: FAILED${NC}"
    echo -e "${YELLOW}   Tip: Run with --fix to auto-fix issues${NC}"
    WALL_STATUS=1
fi

###############################################################################
# STEP 3: Mypy (Type Checking)
###############################################################################

echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 3/4: Mypy (Type Checking)${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"

echo "📝 Running Mypy..."
if $VERBOSE; then
    mypy src/
else
    mypy src/ --no-error-summary 2>&1 | grep -E "error:|Success" || true
fi
MYPY_STATUS=$?

if [ $MYPY_STATUS -eq 0 ]; then
    echo -e "${GREEN}✅ Mypy: PASSED${NC}"
else
    echo -e "${RED}❌ Mypy: FAILED${NC}"
    echo -e "${YELLOW}   Fix type errors before proceeding${NC}"
    WALL_STATUS=1
fi

###############################################################################
# STEP 4: Pytest (Tests)
###############################################################################

if $SKIP_TESTS; then
    echo -e "\n${YELLOW}⏭️  Skipping tests (--skip-tests flag)${NC}"
else
    echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 4/4: Pytest (Tests)${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"

    # Only run tests if previous steps passed
    if [ $WALL_STATUS -ne 0 ]; then
        echo -e "${RED}⚠️  Skipping tests due to previous failures${NC}"
        echo -e "${YELLOW}   Fix Black/Ruff/Mypy issues first${NC}"
    else
        echo "✅ Running Pytest..."

        if $VERBOSE; then
            pytest --cov=src --cov-report=term-missing -v
        else
            # Run with minimal output
            pytest --cov=src --cov-report=term-missing --tb=short -q
        fi
        PYTEST_STATUS=$?

        if [ $PYTEST_STATUS -eq 0 ]; then
            echo -e "${GREEN}✅ Pytest: PASSED${NC}"
        else
            echo -e "${RED}❌ Pytest: FAILED${NC}"
            WALL_STATUS=1
        fi
    fi
fi

###############################################################################
# Summary
###############################################################################

echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}\n"

if [ $WALL_STATUS -eq 0 ]; then
    echo -e "${GREEN}🎉 QUALITY WALL: PASSED ✅${NC}"
    echo -e "${GREEN}All checks completed successfully!${NC}"

    if ! $SKIP_TESTS; then
        echo -e "\n${BLUE}📊 Coverage Report:${NC}"
        echo -e "${YELLOW}   Open: htmlcov/index.html${NC}"
    fi

    exit 0
else
    echo -e "${RED}❌ QUALITY WALL: FAILED${NC}"
    echo -e "${RED}Some checks did not pass. Please fix the issues above.${NC}"

    echo -e "\n${YELLOW}💡 Quick fixes:${NC}"
    echo -e "   • Format code:    ${BLUE}black src/ tests/${NC}"
    echo -e "   • Fix linting:    ${BLUE}ruff check --fix src/ tests/${NC}"
    echo -e "   • Check types:    ${BLUE}mypy src/${NC}"
    echo -e "   • Run tests:      ${BLUE}pytest${NC}"

    exit 1
fi
