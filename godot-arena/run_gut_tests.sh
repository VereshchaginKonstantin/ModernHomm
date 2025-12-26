#!/bin/bash
# Run GUT tests for Godot arena

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Run tests with timeout and capture output
OUTPUT=$(timeout 60 godot --headless --path "$SCRIPT_DIR" --scene test/test_scene.tscn 2>&1)

# Show filtered results
echo "$OUTPUT" | grep -E "(RESULTS|Passed:|Failed:|Total:|ALL TESTS|SOME TESTS)"

# Check for failure
if echo "$OUTPUT" | grep -q "SOME TESTS FAILED"; then
    echo "❌ GUT tests failed!"
    exit 1
else
    echo "✅ GUT tests passed!"
    exit 0
fi
