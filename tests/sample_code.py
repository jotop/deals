SAMPLES = {
"csharp": """namespace Demo {
  public interface IShape { double Area(); }
  public class Circle : IShape {
    private double radius = 2.0;
    public double Area() { int local = 3; return 3.14 * radius * radius; }
  }
  public struct Pt { public int X; }
  public enum Color { Red, Green }
}
""",
"terraform": """terraform {
  required_version = ">= 1.5"
}
provider "aws" {
  region = "eu-central-1"
}
variable "env" {
  type    = string
  default = "dev"
}
locals {
  name = "app-${var.env}"
  tags = { Env = var.env }
}
data "aws_ami" "ubuntu" {
  most_recent = true
}
resource "aws_instance" "web" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.micro"
}
module "vpc" {
  source = "./modules/vpc"
}
output "ip" {
  value = aws_instance.web.public_ip
}
""",
"hcl": """job "web" {
  datacenters = ["dc1"]
  group "cache" {
    count = 1
  }
}
region = "global"
""",
"bash": """#!/bin/bash
GREETING="hello"
export PATH_X=/tmp
greet() {
  local who="$1"
  echo "$GREETING $who"
}
function other { echo hi; }
greet world
""",
"dockerfile": """FROM python:3.12-slim AS base
ARG VERSION=1
ENV APP_HOME=/app
WORKDIR /app
RUN pip install flask
FROM base AS final
COPY . .
CMD ["python", "app.py"]
""",
"make": """CC := gcc
CFLAGS = -O2
.PHONY: all clean
all: main.o util.o
\t$(CC) -o app main.o util.o
clean:
\trm -f *.o
define HELP
x
endef
""",
"cmake": """cmake_minimum_required(VERSION 3.20)
project(demo)
set(SRC main.c)
function(add_thing name)
  message(STATUS ${name})
endfunction()
macro(my_macro)
endmacro()
add_executable(demo ${SRC})
""",
"sql": """CREATE TABLE users (id INT PRIMARY KEY, name TEXT);
CREATE VIEW v_users AS SELECT id FROM users;
CREATE FUNCTION add_one(i integer) RETURNS integer AS $$ BEGIN RETURN i + 1; END; $$ LANGUAGE plpgsql;
CREATE INDEX idx_name ON users (name);
""",
"powershell": """function Get-Thing {
  param([string]$Name)
  $result = "x"
  return $result
}
class Foo {
  [string]$Prop
  [void] Bar() { }
}
$global:count = 3
""",
"scala": """package demo
trait Shape { def area: Double }
class Circle(r: Double) extends Shape {
  val radius = r
  var count = 0
  def area: Double = 3.14 * radius
}
object Main { def main(args: Array[String]): Unit = { val x = 1 } }
case class P(x: Int)
""",
"lua": """local M = {}
local count = 0
function M.add(a, b) return a + b end
function helper(x) return x end
local function inner(y) return y end
Counter = {}
return M
""",
"perl": """package Foo;
use strict;
my $x = 1;
our $y = 2;
sub new { my $class = shift; return bless {}, $class; }
sub greet { print "hi\\n"; }
1;
""",
"dart": """class Animal {
  String name = 'x';
  void speak() { print(name); }
}
abstract class Shape { double area(); }
mixin Walker { void walk() {} }
enum Color { red, green }
int add(int a, int b) { return a + b; }
final answer = 42;
var counter = 0;
""",
"julia": """module Demo
struct Point
  x::Int
end
abstract type Shape end
function area(p::Point)
  return p.x
end
sq(x) = x * x
const LIMIT = 10
y = 5
end
""",
"elixir": """defmodule Demo.Greeter do
  @moduledoc false
  def hello(name) do
    "hi " <> name
  end
  defp secret(x), do: x
  defmacro mymacro(x), do: x
end
""",
"haskell": """module Demo where
data Shape = Circle Double | Rect Double Double
newtype Wrapper = Wrapper Int
class Describable a where
  describe :: a -> String
area :: Shape -> Double
area (Circle r) = 3.14 * r * r
total = 10
""",
"zig": """const std = @import("std");
const Point = struct { x: i32, y: i32 };
const Color = enum { red, green };
pub fn add(a: i32, b: i32) i32 { return a + b; }
var counter: u32 = 0;
pub fn main() void { const z = 1; _ = z; }
""",
"solidity": """pragma solidity ^0.8.0;
interface IToken { function transfer(address to) external; }
contract Token is IToken {
  uint256 public total;
  event Sent(address a);
  function transfer(address to) external override { }
  modifier onlyOwner() { _; }
}
library Math { function max(uint a, uint b) internal pure returns (uint) { return a; } }
""",
"groovy": """class Greeter {
  String name = 'x'
  def greet() { println name }
}
def helper(x) { return x }
def count = 3
""",
"objc": """@interface Foo : NSObject
- (void)bar;
@end
@implementation Foo
- (void)bar { int x = 1; }
@end
int helper(int a) { return a; }
""",
"proto": """syntax = "proto3";
message User { string name = 1; }
enum Role { ADMIN = 0; }
service Api { rpc Get(User) returns (User); }
""",
"graphql": """type User { id: ID! name: String }
interface Node { id: ID! }
enum Role { ADMIN USER }
query GetUser { user { id } }
""",
"fsharp": """module Demo
type Point = { X: int; Y: int }
type Shape = Circle of float | Square of float
let add a b = a + b
let total = 10
""",
"ocaml": """type shape = Circle of float | Square of float
module M = struct let x = 1 end
let area s = match s with Circle r -> r | Square a -> a
let total = 10
""",
"clojure": """(ns demo.core)
(defn greet [name] (str "hi " name))
(def answer 42)
(defmacro twice [x] `(do ~x ~x))
(defrecord Person [name])
""",
"erlang": """-module(demo).
-export([add/2]).
-record(person, {name}).
add(A, B) -> A + B.
sub(A, B) -> A - B.
""",
"matlab": """function r = area(x)
  r = x * x;
end
classdef Foo
  properties
    p
  end
  methods
    function obj = Foo()
    end
  end
end
y = 3;
""",
"fortran": """module demo
  implicit none
contains
  subroutine greet(name)
    character(len=*) :: name
    print *, name
  end subroutine
  function add(a, b) result(c)
    integer :: a, b, c
    c = a + b
  end function
end module
program main
  integer :: x
  x = 1
end program
""",
"nim": """type
  Point = object
    x: int
proc add(a, b: int): int = a + b
var counter = 0
let answer = 42
""",
"nix": """{ pkgs ? import <nixpkgs> {} }:
let
  name = "demo";
  add = a: b: a + b;
in pkgs.mkShell { buildInputs = []; }
""",
"vim": """function! Greet(name)
  echo a:name
endfunction
let g:count = 1
""",
"batch": """@echo off
set NAME=world
:greet
echo hello %NAME%
goto :eof
""",
"asm": """section .text
global _start
_start:
  mov eax, 1
helper:
  ret
""",
"gdscript": """class_name Player
extends Node
var speed = 10
func move(dir):
  pass
class Inner:
  var a = 1
""",
"starlark": """def macro(name):
  native.genrule(name = name)
LIMIT = 3
cc_library(name = "x")
""",
"just": """set shell := ["bash", "-c"]
version := "1"
build:
  cargo build
test arg:
  cargo test
""",
"bicep": """param location string = 'x'
var prefix = 'abc'
resource sa 'Microsoft.Storage/storageAccounts@2021-01-01' = { name: 'x' }
module m './m.bicep' = { name: 'm' }
output id string = sa.id
""",
"rego": """package authz
default allow = false
allow { input.user == "admin" }
is_admin(u) { u == "admin" }
""",
"cue": """package demo
#Schema: { name: string }
x: 1
""",
}
