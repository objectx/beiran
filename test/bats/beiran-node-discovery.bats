#!/usr/bin/env bats

@test "Check if nodes discover each other correctly" {
    result="$(python -m beiran.cli node list |  wc -l)"
    [ "$result" -eq 6 ]
}