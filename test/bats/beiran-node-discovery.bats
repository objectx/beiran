#!/usr/bin/env bats

@test "Check if nodes discover each other correctly" {
    sqlite3 /var/lib/beiran/beiran.db 'select * from node' |  wc -l
    [ $output = 4]
}