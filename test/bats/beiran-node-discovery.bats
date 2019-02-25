#!/usr/bin/env bats

@test "Check if nodes discover each other correctly" {
    result="$(beiran node list | cut -d ' ' -f1 | grep -x '[_[:alnum:]]\{32\}' | wc -l)"
    [ "$result" -eq 4 ]
}