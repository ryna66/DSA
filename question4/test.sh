#!/bin/sh
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$PROJECT_DIR/build"
javac --release 17 --add-modules jdk.httpserver -d "$PROJECT_DIR/build" "$PROJECT_DIR"/src/*.java "$PROJECT_DIR"/tests/*.java
java --add-modules jdk.httpserver -cp "$PROJECT_DIR/build" ExamSchedulerTest
