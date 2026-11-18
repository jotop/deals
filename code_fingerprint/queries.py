"""Tree-sitter queries that pull class / function / variable names out of source.

Keys are ``tree_sitter_language_pack`` names.  Every pattern captures a name
node as ``@class.name``, ``@function.name`` or ``@variable.name``; the part
before the dot is the symbol kind that ends up in the fingerprint.

Languages without an entry here still get a fingerprint from the generic
fallback in :mod:`.symbols`, which looks for ``*_declaration`` /
``*_definition`` nodes that have a ``name`` field.  Add an entry when that
fallback finds nothing (check with ``tests/test_queries.py``).

Mapping used for infrastructure languages (they have no real classes or
functions):

* Terraform / HCL   ``resource`` / ``data`` types, ``module`` and ``provider``
  names are *classes*; resource instance names, ``variable`` / ``output``
  names and ``locals`` entries are *variables*.
* Dockerfile        build-stage aliases are *classes*; ``ARG`` / ``ENV`` names
  are *variables*.
* Make / CMake      targets, functions and macros are *functions*.
"""

from __future__ import annotations

from typing import Dict, List

QUERIES: Dict[str, List[str]] = {

    # --- Languages that shipped with the original script (patterns unchanged)
    "python": [
        "(class_definition name: (identifier) @class.name)",
        "(function_definition name: (identifier) @function.name)",
        "(assignment left: (identifier) @variable.name)",
    ],
    "javascript": [
        "(class_declaration name: (identifier) @class.name)",
        "(function_declaration name: (identifier) @function.name)",
        "(generator_function_declaration name: (identifier) @function.name)",
        "(method_definition name: (property_identifier) @function.name)",
        "(variable_declarator name: (identifier) @variable.name)",
    ],
    "typescript": [
        "(class_declaration name: (type_identifier) @class.name)",
        "(abstract_class_declaration name: (type_identifier) @class.name)",
        "(interface_declaration name: (type_identifier) @class.name)",
        "(enum_declaration name: (identifier) @class.name)",
        "(function_declaration name: (identifier) @function.name)",
        "(method_definition name: (property_identifier) @function.name)",
        "(variable_declarator name: (identifier) @variable.name)",
    ],
    "c": [
        "(struct_specifier name: (type_identifier) @class.name body: (_))",
        "(union_specifier name: (type_identifier) @class.name body: (_))",
        "(enum_specifier name: (type_identifier) @class.name body: (_))",
        "(function_definition declarator: (function_declarator declarator: (identifier) @function.name))",
        "(function_definition declarator: (pointer_declarator declarator: (function_declarator declarator: (identifier) @function.name)))",
        "(init_declarator declarator: (identifier) @variable.name)",
        "(init_declarator declarator: (pointer_declarator declarator: (identifier) @variable.name))",
        "(declaration declarator: (identifier) @variable.name)",
    ],
    "cpp": [
        "(class_specifier name: (type_identifier) @class.name body: (_))",
        "(struct_specifier name: (type_identifier) @class.name body: (_))",
        "(function_definition declarator: (function_declarator declarator: [(identifier) (field_identifier) (qualified_identifier)] @function.name))",
        "(function_definition declarator: (pointer_declarator declarator: (function_declarator declarator: [(identifier) (qualified_identifier)] @function.name)))",
        "(init_declarator declarator: (identifier) @variable.name)",
        "(declaration declarator: (identifier) @variable.name)",
        "(field_declaration declarator: (field_identifier) @variable.name)",
    ],
    "r": [
        '(binary_operator lhs: (identifier) @function.name operator: ["<-" "=" "<<-"] rhs: (function_definition))',
        '(binary_operator lhs: (identifier) @variable.name operator: ["<-" "=" "<<-"])',
    ],
    "swift": [
        "(class_declaration name: (type_identifier) @class.name)",
        "(protocol_declaration name: (type_identifier) @class.name)",
        "(function_declaration name: (simple_identifier) @function.name)",
        "(protocol_function_declaration name: (simple_identifier) @function.name)",
        "(property_declaration name: (pattern bound_identifier: (simple_identifier) @variable.name))",
        "(property_declaration name: (pattern (simple_identifier) @variable.name))",
    ],
    "rust": [
        "(struct_item name: (type_identifier) @class.name)",
        "(enum_item name: (type_identifier) @class.name)",
        "(trait_item name: (type_identifier) @class.name)",
        "(union_item name: (type_identifier) @class.name)",
        "(function_item name: (identifier) @function.name)",
        "(function_signature_item name: (identifier) @function.name)",
        "(let_declaration pattern: (identifier) @variable.name)",
        "(const_item name: (identifier) @variable.name)",
        "(static_item name: (identifier) @variable.name)",
    ],
    "go": [
        "(type_spec name: (type_identifier) @class.name)",
        "(function_declaration name: (identifier) @function.name)",
        "(method_declaration name: (field_identifier) @function.name)",
        "(var_spec name: (identifier) @variable.name)",
        "(const_spec name: (identifier) @variable.name)",
        "(short_var_declaration left: (expression_list (identifier) @variable.name))",
    ],
    "java": [
        "(class_declaration name: (identifier) @class.name)",
        "(interface_declaration name: (identifier) @class.name)",
        "(enum_declaration name: (identifier) @class.name)",
        "(record_declaration name: (identifier) @class.name)",
        "(method_declaration name: (identifier) @function.name)",
        "(constructor_declaration name: (identifier) @function.name)",
        "(variable_declarator name: (identifier) @variable.name)",
    ],
    "ruby": [
        "(class name: (constant) @class.name)",
        "(module name: (constant) @class.name)",
        "(method name: (identifier) @function.name)",
        "(singleton_method name: (identifier) @function.name)",
        "(assignment left: (identifier) @variable.name)",
    ],
    "php": [
        "(class_declaration name: (name) @class.name)",
        "(interface_declaration name: (name) @class.name)",
        "(trait_declaration name: (name) @class.name)",
        "(function_definition name: (name) @function.name)",
        "(method_declaration name: (name) @function.name)",
        "(assignment_expression left: (variable_name (name) @variable.name))",
    ],
    "kotlin": [
        "(class_declaration (type_identifier) @class.name)",
        "(object_declaration (type_identifier) @class.name)",
        "(function_declaration (simple_identifier) @function.name)",
        "(property_declaration (variable_declaration (simple_identifier) @variable.name))",
    ],

    # --- C#  (key was ``c_sharp`` before, which is not a tree-sitter-language-pack name, so it never matched)
    "csharp": [
        "(class_declaration name: (identifier) @class.name)",
        "(struct_declaration name: (identifier) @class.name)",
        "(interface_declaration name: (identifier) @class.name)",
        "(enum_declaration name: (identifier) @class.name)",
        "(record_declaration name: (identifier) @class.name)",
        "(method_declaration name: (identifier) @function.name)",
        "(constructor_declaration name: (identifier) @function.name)",
        "(local_function_statement name: (identifier) @function.name)",
        "(variable_declarator (identifier) @variable.name)",
    ],

    # --- Infrastructure / configuration as code
    "terraform": [
        '(block (identifier) @_k . (string_lit (template_literal) @class.name) . (string_lit) (#any-of? @_k "resource" "data"))',
        '(block (identifier) @_k (string_lit) . (string_lit (template_literal) @variable.name) (#any-of? @_k "resource" "data"))',
        '(block (identifier) @_k . (string_lit (template_literal) @class.name) (#any-of? @_k "module" "provider"))',
        '(block (identifier) @_k . (string_lit (template_literal) @variable.name) (#any-of? @_k "variable" "output"))',
        '(block (identifier) @_k (body (attribute (identifier) @variable.name)) (#eq? @_k "locals"))',
    ],
    "hcl": [
        "(config_file (body (block (identifier) @class.name)))",
        "(config_file (body (block (identifier) . (string_lit (template_literal) @class.name))))",
        "(config_file (body (attribute (identifier) @variable.name)))",
        '(block (identifier) @_k (body (attribute (identifier) @variable.name)) (#eq? @_k "locals"))',
    ],
    "bicep": [
        "(parameter_declaration (identifier) @variable.name)",
        "(variable_declaration (identifier) @variable.name)",
        "(output_declaration (identifier) @variable.name)",
        "(resource_declaration (identifier) @class.name)",
        "(module_declaration (identifier) @class.name)",
        "(type_declaration (identifier) @class.name)",
    ],
    "dockerfile": [
        "(from_instruction as: (image_alias) @class.name)",
        "(arg_instruction name: (unquoted_string) @variable.name)",
        "(env_instruction (env_pair name: (unquoted_string) @variable.name))",
    ],
    "make": [
        '(rule (targets (word) @function.name) (#not-match? @function.name "^[.]"))',
        "(variable_assignment name: (word) @variable.name)",
        "(define_directive name: (word) @variable.name)",
    ],
    "cmake": [
        "(function_def (function_command (argument_list . (argument) @function.name)))",
        "(macro_def (macro_command (argument_list . (argument) @function.name)))",
        '(normal_command (identifier) @_c (argument_list . (argument) @variable.name) (#match? @_c "^(set|option|project)$"))',
    ],
    "nix": [
        "(binding attrpath: (attrpath . (identifier) @function.name) expression: (function_expression))",
        "(binding attrpath: (attrpath . (identifier) @variable.name))",
    ],

    # --- Shells and scripting
    "bash": [
        "(function_definition name: (word) @function.name)",
        "(variable_assignment name: (variable_name) @variable.name)",
    ],
    "powershell": [
        "(class_statement (simple_name) @class.name)",
        "(function_statement (function_name) @function.name)",
        "(class_method_definition (simple_name) @function.name)",
        "(class_property_definition (variable) @variable.name)",
    ],
    "lua": [
        "(function_declaration name: (identifier) @function.name)",
        "(function_declaration name: (dot_index_expression field: (identifier) @function.name))",
        "(function_declaration name: (method_index_expression method: (identifier) @function.name))",
        "(assignment_statement (variable_list name: (identifier) @variable.name))",
    ],
    "perl": [
        "(package_statement name: (package) @class.name)",
        "(subroutine_declaration_statement name: (bareword) @function.name)",
        "(variable_declaration (scalar) @variable.name)",
        "(variable_declaration (array) @variable.name)",
        "(variable_declaration (hash) @variable.name)",
    ],

    # --- Other general-purpose languages
    "scala": [
        "(class_definition name: (identifier) @class.name)",
        "(trait_definition name: (identifier) @class.name)",
        "(object_definition name: (identifier) @class.name)",
        "(enum_definition name: (identifier) @class.name)",
        "(function_definition name: (identifier) @function.name)",
        "(function_declaration name: (identifier) @function.name)",
        "(val_definition pattern: (identifier) @variable.name)",
        "(var_definition pattern: (identifier) @variable.name)",
    ],
    "dart": [
        "(class_definition name: (identifier) @class.name)",
        "(mixin_declaration (identifier) @class.name)",
        "(enum_declaration name: (identifier) @class.name)",
        "(extension_declaration name: (identifier) @class.name)",
        "(function_signature name: (identifier) @function.name)",
        "(initialized_identifier (identifier) @variable.name)",
        "(static_final_declaration (identifier) @variable.name)",
    ],
    "julia": [
        "(module_definition name: (identifier) @class.name)",
        "(struct_definition (type_head (identifier) @class.name))",
        "(abstract_definition (type_head (identifier) @class.name))",
        "(function_definition (signature (call_expression . (identifier) @function.name)))",
        "(assignment . (call_expression . (identifier) @function.name))",
        "(assignment . (identifier) @variable.name)",
    ],
    "elixir": [
        '(call target: (identifier) @_d (arguments (alias) @class.name) (#any-of? @_d "defmodule" "defprotocol" "defimpl"))',
        '(call target: (identifier) @_d (arguments (call target: (identifier) @function.name)) (#any-of? @_d "def" "defp" "defmacro" "defmacrop" "defguard" "defdelegate"))',
        '(call target: (identifier) @_d (arguments . (identifier) @function.name) (#any-of? @_d "def" "defp" "defmacro" "defmacrop"))',
    ],
    "haskell": [
        "(data_type name: (name) @class.name)",
        "(newtype name: (name) @class.name)",
        "(class name: (name) @class.name)",
        "(type_synonym name: (name) @class.name)",
        "(function name: (variable) @function.name)",
        "(bind name: (variable) @variable.name)",
    ],
    "zig": [
        "(function_declaration name: (identifier) @function.name)",
        "(variable_declaration (identifier) @class.name [(struct_declaration) (enum_declaration) (union_declaration) (opaque_declaration)])",
        '(variable_declaration . (identifier) @variable.name (#not-eq? @variable.name "_"))',
    ],
    "solidity": [
        "(contract_declaration name: (identifier) @class.name)",
        "(interface_declaration name: (identifier) @class.name)",
        "(library_declaration name: (identifier) @class.name)",
        "(struct_declaration name: (identifier) @class.name)",
        "(enum_declaration name: (identifier) @class.name)",
        "(event_definition name: (identifier) @class.name)",
        "(error_declaration name: (identifier) @class.name)",
        "(function_definition name: (identifier) @function.name)",
        "(modifier_definition name: (identifier) @function.name)",
        "(state_variable_declaration name: (identifier) @variable.name)",
    ],
    "objc": [
        "(class_interface . (identifier) @class.name)",
        "(class_implementation . (identifier) @class.name)",
        "(protocol_declaration . (identifier) @class.name)",
        "(method_definition (identifier) @function.name)",
        "(method_declaration (identifier) @function.name)",
        "(function_definition declarator: (function_declarator declarator: (identifier) @function.name))",
        "(init_declarator declarator: (identifier) @variable.name)",
    ],
    "fsharp": [
        "(type_name type_name: (identifier) @class.name)",
        "(function_declaration_left . (identifier) @function.name)",
        "(value_declaration_left (identifier_pattern (long_identifier_or_op (identifier) @variable.name)))",
    ],
    "ocaml": [
        "(type_binding name: (type_constructor) @class.name)",
        "(module_binding (module_name) @class.name)",
        "(let_binding pattern: (value_name) @function.name (parameter))",
        "(let_binding pattern: (value_name) @variable.name)",
    ],
    "clojure": [
        '(list_lit . (sym_lit name: (sym_name) @_d) . (sym_lit name: (sym_name) @function.name) (#any-of? @_d "defn" "defn-" "defmacro" "defmulti" "defmethod"))',
        '(list_lit . (sym_lit name: (sym_name) @_d) . (sym_lit name: (sym_name) @variable.name) (#any-of? @_d "def" "defonce"))',
        '(list_lit . (sym_lit name: (sym_name) @_d) . (sym_lit name: (sym_name) @class.name) (#any-of? @_d "ns" "defrecord" "deftype" "defprotocol" "definterface"))',
    ],
    "erlang": [
        "(module_attribute name: (atom) @class.name)",
        "(record_decl name: (atom) @class.name)",
        "(fun_decl clause: (function_clause name: (atom) @function.name))",
    ],

    # --- Query and interface-definition languages
    "sql": [
        "(create_table (object_reference name: (identifier) @class.name))",
        "(create_view (object_reference name: (identifier) @class.name))",
        "(create_function (object_reference name: (identifier) @function.name))",
    ],
    "proto": [
        "(message (message_name (identifier) @class.name))",
        "(enum (enum_name (identifier) @class.name))",
        "(service (service_name (identifier) @class.name))",
        "(rpc (rpc_name (identifier) @function.name))",
        "(field (identifier) @variable.name)",
    ],
    "graphql": [
        "(object_type_definition (name) @class.name)",
        "(interface_type_definition (name) @class.name)",
        "(enum_type_definition (name) @class.name)",
        "(input_object_type_definition (name) @class.name)",
        "(union_type_definition (name) @class.name)",
        "(scalar_type_definition (name) @class.name)",
        "(operation_definition (name) @function.name)",
        "(fragment_definition (fragment_name (name) @function.name))",
        "(field_definition (name) @variable.name)",
    ],
}

# Grammars that share node names with another one reuse its patterns.
QUERIES["tsx"] = QUERIES["typescript"]
QUERIES["zsh"] = QUERIES["bash"]
