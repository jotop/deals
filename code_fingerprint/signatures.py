"""Regex signatures used by the content-based language detector.

Each language is described by a list of :class:`Sig` objects.  A signature adds
``weight`` to the language's score for every match of ``rx`` in the text (at
most ``cap`` matches are counted); negative weights act as penalties.

The language keys in :data:`SIGNATURES` are ``tree_sitter_language_pack``
identifiers (``cpp``, ``csharp``, ``bash``, ``make``, ``asm`` ...), so whatever
the detector returns can be handed straight to the parser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Pattern


@dataclass(frozen=True)
class Sig:
    rx: Pattern[str]
    weight: float          # score added per match (may be negative)
    cap: int               # max number of matches that are counted


def S(pattern: str, weight: float, cap: int = 4, flags: int = 0) -> Sig:
    return Sig(re.compile(pattern, re.M | flags), weight, cap)


_PYTHON = [
    S(r"^#!.*\bpython", 10, 1),
    S(r"^\s*def\s+\w+\s*\([^)]*\)\s*(->\s*[^:]+)?:\s*(#.*)?$", 5, 5),
    S(r"^\s*class\s+\w+\s*(\([^)]*\))?\s*:\s*(#.*)?$", 5, 3),
    S(r"^\s*(from\s+[\w.]+\s+import\s+\S|import\s+[\w.]+(\s+as\s+\w+)?(\s*,\s*[\w.]+)*\s*$)", 3, 4),
    S(r"^\s*(if|elif|else|for|while|try|except|finally|with)\b[^\n{};]*:\s*(#.*)?$", 2.5, 6),
    S(r"\bif\s+__name__\s*==\s*['\"]__main__['\"]", 10, 1),
    S(r"\bself\.\w+", 2, 5),
    S(r"^\s*@\w+(\.\w+)*(\(.*\))?\s*$", 1, 3),
    S(r"\bprint\s*\(", 1, 3),
    S(r"\b(True|False|None)\b", 1.5, 4),
    S(r"\blambda\b[^:\n]*:", 2, 2),
    S(r"\belif\b", 3, 2),
    S(r"\bf(['\"])[^\n]*\{[^\n]*\}[^\n]*\1", 3, 3),
    S(r"\bin\s+range\s*\(", 3, 3),
    S(r"^\s*pass\s*$", 2, 2),
    S(r"\b(is\s+not|not\s+in)\b", 2, 2),
    S(r"\bdef\s+__\w+__\s*\(", 5, 2),
    S(r"\basync\s+def\b", 4, 2),
    S(r"\bwith\s+open\s*\(", 5, 1),
    S(r"\bexcept\s+(\w+(\.\w+)*\s*)?(as\s+\w+\s*)?:", 4, 2),
    S(r"\braise\s+\w+", 1.5, 2),
    S(r"\blen\s*\(", 1.5, 3),
    S(r"^\s*\"\"\"", 2, 2),
    S(r"^\s*import\s+(numpy|pandas|os|sys|re|json|math|random|time|datetime|collections|itertools|typing|argparse|subprocess|logging|pathlib|requests|matplotlib|unittest|functools|dataclasses|asyncio)\b", 4, 4),
    S(r"^\s*import\s+\w+\s+as\s+\w+\s*$", 3, 3),
    S(r"\b(np|pd|plt)\.\w+", 2, 4),
    S(r"\b(os|sys)\.(path|argv|environ|exit)\b", 3, 3),
    # C-style punctuation is rare in Python -> penalties
    S(r";\s*$", -2, 5),
    S(r"^\s*\}\s*$", -3, 3),
    S(r"\{\s*$", -1.5, 4),
]

_JS = [
    S(r"^#!.*\bnode\b", 10, 1),
    S(r"\bfunction\s*\*?\s*\w*\s*\(", 3, 4),
    S(r"\b(const|let|var)\s+[\w${}\[\], ]+\s*=", 1.5, 6),
    S(r"=>", 1.5, 5),
    S(r"\bconsole\.(log|error|warn|info|debug)\s*\(", 6, 3),
    S(r"\brequire\s*\(\s*['\"]", 5, 3),
    S(r"\bmodule\.exports\b|\bexports\.\w+\s*=", 6, 2),
    S(r"^\s*import\s+[^;\n]*\s+from\s+['\"]", 4, 3),
    S(r"^\s*export\s+(default|const|let|function|class|async|\{)", 4, 3),
    S(r"===|!==", 3, 4),
    S(r"\bdocument\.(getElementById|querySelector(All)?|addEventListener|createElement|body)", 6, 3),
    S(r"\bwindow\.\w+", 2, 3),
    S(r"\.then\s*\(|\bnew\s+Promise\b|\bPromise\.(all|resolve|reject)\b", 3, 3),
    S(r"\bawait\s+\w", 1, 3),
    S(r"\.(map|filter|reduce|forEach|find|some|every)\s*\(", 1.5, 4),
    S(r"`[^`\n]*\$\{[^}\n]+\}[^`\n]*`", 3, 3),
    S(r"\btypeof\s+\w+|\bundefined\b", 2, 3),
    S(r"\bJSON\.(parse|stringify)\s*\(", 3, 2),
    S(r"\bnew\s+(Map|Set|Array|Date|Error|RegExp)\s*\(", 2, 3),
    S(r"\bthis\.\w+", 1, 4),
    S(r"\b(setTimeout|setInterval|addEventListener|fetch)\s*\(|\blocalStorage\.", 3, 2),
    S(r"\b\w+\s*:\s*function\s*\(", 3, 2),
    S(r"\$\(['\"][^'\"]+['\"]\)", 3, 2),
]

_TS_EXTRA = [
    S(r":\s*(string|number|boolean|any|void|unknown|never|object)\b(\[\])?", 4, 6),
    S(r"^\s*(export\s+)?(declare\s+)?interface\s+\w+(<[^>]*>)?\s*(extends\s+[\w, <>]+)?\s*\{", 5, 3),
    S(r"^\s*(export\s+)?type\s+\w+(<[^>]*>)?\s*=", 6, 3),
    S(r"\b(Array|Promise|Record|Partial|Readonly|Map|Set)<[\w\[\]<>,| ]+>", 3, 4),
    S(r"\)\s*:\s*[\w<>\[\]| ]+\s*(=>|\{)", 3, 4),
    S(r"\b(readonly|private|public|protected)\s+\w+\s*[:?]", 3, 3),
    S(r"\w\?\s*:\s*\w+", 3, 3),
    S(r"\bas\s+(any|unknown|const|string|number|\w+\[\])\b", 3, 2),
    S(r"\bimplements\s+\w+|\babstract\s+class\b", 2, 2),
    S(r"@(Component|Injectable|NgModule|Input|Output)\b", 6, 2),
    S(r"\bimport\s+type\b", 5, 1),
]

_JAVA = [
    S(r"\bpublic\s+static\s+void\s+main\s*\(\s*String", 12, 1),
    S(r"\bSystem\.(out|err)\.(println|print|printf)\s*\(", 7, 3),
    S(r"^\s*import\s+(java|javax|org|com|android)\.[\w.*]+;", 7, 4),
    S(r"^\s*package\s+[\w.]+\s*;", 5, 1),
    S(r"^\s*(public\s+|private\s+|protected\s+)?(abstract\s+|final\s+|static\s+)*(class|interface|enum)\s+\w+", 3, 3),
    S(r"@(Override|Autowired|Test|Entity|Service|Component|RestController|Repository|SuppressWarnings|FunctionalInterface|Deprecated|Getter|Setter|Bean|RequestMapping|GetMapping|PostMapping)\b", 4, 4),
    S(r"\b(String|Integer|Boolean|Double|Long|Object)\s+\w+\s*(=|;|\)|,)", 2, 5),
    S(r"\b(List|ArrayList|Map|HashMap|Set|HashSet|Optional|LinkedList|Deque|Queue)<[\w<>, ?]*>", 3, 4),
    S(r"\bthrows\s+\w+", 4, 2),
    S(r"\bimplements\s+\w+", 3, 2),
    S(r"\bextends\s+\w+", 1.5, 2),
    S(r"\b(public|private|protected)\s+(static\s+)?(final\s+)?[\w<>\[\], ]+\s+\w+\s*\([^)]*\)\s*(throws\s+[\w, ]+)?\s*\{", 3, 4),
    S(r"\.(equals|length|size|isEmpty|toString|hashCode|getClass)\s*\(", 1.5, 4),
    S(r"\bnew\s+[A-Z]\w*(<[^>]*>)?\s*\(", 1, 4),
    S(r"\bfinal\s+[A-Z]?\w+(<[^>]*>)?\s+\w+\s*=", 2, 3),
    S(r"\b(instanceof|synchronized|transient|volatile)\b", 2, 2),
    S(r"\b(boolean|byte)\s+\w+", 2.5, 3),
    S(r"\bString\[\]", 3, 2),
    S(r"\bthis\.\w+\s*=\s*\w+;", 1.5, 3),
]

_C = [
    S(r"^\s*#\s*include\s*[<\"][\w/.]+\.h[>\"]", 5, 4),
    S(r"\b(printf|scanf|fprintf|sprintf|snprintf|puts|fgets|fputs|fopen|fclose|getchar|putchar)\s*\(", 3, 4),
    S(r"\b(malloc|calloc|realloc|free)\s*\(", 4, 3),
    S(r"\bint\s+main\s*\(\s*(void|int\s+argc\b[^)]*)?\)", 7, 1),
    S(r"\bsizeof\s*\(?", 2, 2),
    S(r"\btypedef\s+(struct|enum|union)?", 4, 2),
    S(r"\b(struct|union|enum)\s+\w+\s*\{", 2, 3),
    S(r"^\s*#\s*(define|ifdef|ifndef|endif|pragma|undef|elif)\b", 3, 3),
    S(r"(?<![\$\w])\w+->\w+", 1.5, 4),
    S(r"\bNULL\b", 2, 3),
    S(r"\bvoid\s*\*|\bconst\s+char\s*\*|\bchar\s*\*+\s*\w+", 3, 3),
    S(r"\b(unsigned|signed)\s+(char|short|int|long)\b|\b(uint|int)(8|16|32|64)_t\b|\bsize_t\b", 3, 4),
    S(r"\bstatic\s+(inline\s+)?(const\s+)?\w+[\s*]+\w+\s*\(", 1.5, 3),
    S(r"\bint\s+\w+\s*(\[\w*\])?\s*(=|;|,)", 0.8, 5),
    S(r"\breturn\s+(0|1|-1|EXIT_SUCCESS|EXIT_FAILURE)\s*;", 2, 2),
    S(r"\bfor\s*\(\s*int\s+\w+\s*=\s*\d+\s*;", 1.5, 3),
]

_CPP_EXTRA = [
    S(r"^\s*#\s*include\s*<(iostream|vector|string|map|set|algorithm|memory|cstdio|cstdlib|cmath|fstream|sstream|thread|mutex|unordered_map|unordered_set|queue|stack|list|array|functional|iomanip|numeric|utility|tuple|chrono|random|cstring|cstdint|bitset|deque|optional|variant|filesystem|atomic|cassert|climits|ctime)>", 9, 4),
    S(r"\bstd::\w+", 6, 6),
    S(r"\b(cout|cin|cerr|endl)\b\s*(<<|>>|;)", 7, 3),
    S(r"^\s*using\s+namespace\s+\w+\s*;", 7, 1),
    S(r"\btemplate\s*<[^>]*>", 6, 2),
    S(r"^\s*(public|private|protected)\s*:", 6, 3),
    S(r"\bnullptr\b", 6, 2),
    S(r"\bauto\s*[&*]?\s+\w+\s*=", 3, 2),
    S(r"\bdelete\s*(\[\]\s*)?\w+\s*;", 4, 2),
    S(r"\bnew\s+\w+(<[^>]*>)?\s*(\(|\[)", 1.5, 3),
    S(r"\b(virtual|override|constexpr|noexcept|typename|explicit|mutable|friend|decltype|static_cast|dynamic_cast|reinterpret_cast|const_cast)\b", 4, 3),
    S(r"\boperator\s*(==|!=|<=|>=|<<|>>|<|>|\+|-|\*|/|\[\]|\(\)|=)", 4, 2),
    S(r"\b\w+::\w+", 1.5, 5),
    S(r"\bconst\s+[\w:<>]+\s*&\s*\w+", 3, 3),
    S(r"^\s*(class|struct)\s+\w+\s*(final\s*)?(:\s*(public|private|protected)\s+[\w:<>]+\s*)?\{?\s*$", 3, 3),
    S(r"\b(vector|map|set|unique_ptr|shared_ptr)\s*<", 4, 3),
    S(r"\[\s*[&=]?\s*\]\s*\([^)]*\)\s*(->\s*\w+\s*)?\{", 4, 2),
]

_CSHARP = [
    S(r"^\s*using\s+System(\.[\w.]+)?\s*;", 9, 3),
    S(r"^\s*using\s+(static\s+)?[\w.]+\s*;", 2, 3),
    S(r"^\s*namespace\s+[\w.]+\s*(\{|;)?\s*$", 3, 1),
    S(r"^\s*namespace\s+\w+\.[\w.]+", 5, 1),
    S(r"\bConsole\.(WriteLine|Write|ReadLine|ReadKey)\s*\(", 9, 3),
    S(r"\bstring\s+\w+\s*(=|;|\)|,)", 2, 4),
    S(r"\{\s*get\s*;\s*(private\s+|protected\s+)?(set|init)\s*;\s*\}", 8, 3),
    S(r"^\s*\[(Serializable|HttpGet|HttpPost|HttpPut|HttpDelete|Fact|Theory|Test|TestMethod|TestFixture|Required|Route|ApiController|Authorize|JsonProperty|Key|Display)\b[^\]]*\]", 5, 3),
    S(r"\basync\s+Task(<[^>]*>)?\b", 7, 2),
    S(r"\bawait\s+[\w.]+Async\s*\(", 5, 2),
    S(r"\bforeach\s*\(\s*(var|[\w<>\[\]?]+)\s+\w+\s+in\b", 7, 2),
    S(r"\b(public|private|protected|internal)\s+(static\s+)?(override|virtual|abstract|sealed|async|readonly|partial)\b", 4, 3),
    S(r"\b(internal|sealed|partial)\s+(class|struct|record|interface)\b", 5, 2),
    S(r"\b(string|String)\.(Format|IsNullOrEmpty|IsNullOrWhiteSpace|Join|Empty)\b", 5, 2),
    S(r"\b(List|IList|IEnumerable|Dictionary|Task)<\w[\w<>, ]*>", 3, 3),
    S(r"\.(Where|Select|OrderBy|ToList|FirstOrDefault|Any|ToArray|Sum)\s*\(", 3, 3),
    S(r"\bnameof\s*\(|\bvar\s+\w+\s*=\s*new\b", 2, 2),
    S(r"\$\"[^\"\n]*\{[^}\n]+\}[^\"\n]*\"", 4, 2),
    S(r"\bpublic\s+\w+(<[^>]*>)?\s+\w+\s*\(", 1.5, 4),
    S(r"\b(get|set)\s*(;|\{|=>)", 2, 3),
    S(r"#region|#endregion", 6, 2),
    S(r"\b(bool|Guid|DateTime|TimeSpan|decimal)\s+\w+", 3, 3),
]

_GO = [
    S(r"^\s*package\s+\w+\s*$", 6, 1),
    S(r"^\s*import\s+(\(|\"[\w/.\-]+\")", 4, 2),
    S(r"\bfunc\s+(\(\s*\w+\s+\*?\w+\s*\)\s*)?\w+\s*\(", 6, 4),
    S(r"\bfunc\s*\(", 3, 2),
    S(r"\w+(\s*,\s*\w+)*\s*:=", 4, 5),
    S(r"\bfmt\.(Println|Printf|Sprintf|Errorf|Fprintf|Print|Sprint|Fprintln)\s*\(", 9, 3),
    S(r"\bgo\s+(func\b|\w+\()", 5, 2),
    S(r"^\s*defer\s+", 6, 2),
    S(r"\bchan\s+\w+|<-\s*\w+", 4, 2),
    S(r"\bif\s+err\s*!=\s*nil\b", 9, 2),
    S(r"\btype\s+\w+\s+(struct|interface)\s*\{", 9, 2),
    S(r"\bmake\s*\(\s*(\[\]|map\[|chan\s)", 6, 2),
    S(r"\[\]\w+|\bmap\[\w+\]\w+", 3, 3),
    S(r"\bnil\b", 2, 3),
    S(r"\b(strings|strconv|os|errors|time|sync|http|json|bytes|bufio|io|log)\.\w+\(", 2, 4),
    S(r"\bfor\s+\w+\s*,\s*\w+\s*:=\s*range\b", 8, 2),
    S(r"\bvar\s+\w+\s+[\w\[\]*.]+(\s*=|\s*$)", 1.5, 3),
    S(r"\bfunc\s+main\s*\(\s*\)", 8, 1),
    S(r"\berror\b\s*\)?\s*\{\s*$", 3, 2),
]

_RUST = [
    S(r"\bfn\s+\w+\s*(<[^>]*>)?\s*\(", 6, 4),
    S(r"\bfn\s+main\s*\(\s*\)", 8, 1),
    S(r"\blet\s+mut\s+\w+", 7, 3),
    S(r"\blet\s+\w+\s*(:\s*[\w<>&\[\]:', ]+)?\s*=", 1.5, 4),
    S(r"\b(println|print|eprintln|eprint|format|vec|panic|assert|assert_eq|write|writeln|todo|unimplemented|matches)!\s*[\(\[{]", 8, 3),
    S(r"^\s*use\s+(std|crate|super|self|core|alloc)\b(::[\w{}*, :]+)?\s*;", 8, 3),
    S(r"^\s*use\s+\w+(::[\w{}*, ]+)+\s*;", 5, 2),
    S(r"\bimpl\s*(<[^>]*>)?\s+(\w+(<[^>]*>)?\s+for\s+)?\w+", 6, 2),
    S(r"\bpub(\([\w:]+\))?\s+(fn|struct|enum|mod|trait|use|const|static|type)\b", 6, 3),
    S(r"^\s*(pub\s+)?(struct|enum|trait|mod)\s+\w+", 2, 3),
    S(r"\)\s*->\s*[\w<>&\[\]:', ]+\s*(where\b.*)?\{\s*$", 2.5, 3),
    S(r"\b(Option|Result|Vec|Box|Rc|Arc|HashMap|HashSet|RefCell|Mutex)<", 4, 4),
    S(r"\b(Some|Ok|Err)\(|=>\s*None\b", 2, 4),
    S(r"&mut\s+\w+|&'\w+|'static\b|<'\w+>", 5, 3),
    S(r"\bmatch\s+[^\n{]+\{\s*$", 3, 2),
    S(r"#!?\[(derive|allow|cfg|test|inline|warn|deny|macro_use|tokio::main)[^\]]*\]", 9, 2),
    S(r"\.(unwrap|expect|unwrap_or|unwrap_or_else|ok_or|iter|into_iter|collect|clone|to_string|to_owned|as_str|map_err)\s*\(", 2, 5),
    S(r"\b\w+::new\s*\(|\b\w+::from\s*\(|\bSelf\b", 3, 3),
    S(r"\b(i8|i16|i32|i64|i128|isize|u8|u16|u32|u64|u128|usize|f32|f64)\b", 2, 4),
    S(r"\?\s*;", 3, 3),
]

_PHP = [
    S(r"<\?php\b", 12, 1),
    S(r"<\?=", 5, 1),
    S(r"\$\w+", 1.5, 8),
    S(r"\$this->\w+", 6, 3),
    S(r"\b(echo|print)\s+[\"'$]", 3, 3),
    S(r"\bfunction\s+\w+\s*\([^)]*\$", 5, 3),
    S(r"=>", 1, 3),
    S(r"\barray\s*\(", 4, 3),
    S(r"\b(isset|empty|unset|array_\w+|str_\w+|strlen|strpos|implode|explode|json_encode|json_decode|var_dump|print_r|preg_\w+|mysqli_\w+|htmlspecialchars|file_get_contents|in_array|is_array|is_null)\s*\(", 3, 5),
    S(r"\b(public|private|protected)\s+(static\s+)?(function|\$)", 5, 3),
    S(r"\b[A-Z]\w*::\w+|\bself::|\bstatic::|\bparent::", 1.5, 4),
    S(r"^\s*namespace\s+[\w\\]+\s*;", 6, 1),
    S(r"^\s*use\s+\w+(\\\w+)+(\s+as\s+\w+)?\s*;", 6, 3),
    S(r"\$_(GET|POST|SERVER|SESSION|COOKIE|REQUEST|FILES|ENV)\b", 9, 2),
    S(r"\bforeach\s*\(\s*\$\w+\s+as\b", 8, 2),
    S(r"\?>", 2, 1),
    S(r"\$\w+\s*\.=|\.\s*\$\w+|\$\w+\s*\.\s*['\"]", 3, 3),
    S(r"\b(require_once|include_once)\b|\b(require|include)\s*\(?\s*(__DIR__|\$)", 4, 2),
]

_RUBY = [
    S(r"^#!.*\bruby\b", 10, 1),
    S(r"^\s*def\s+(self\.)?\w+[?!=]?(\([^)]*\))?\s*$", 5, 4),
    S(r"^\s*end\s*$", 3, 6),
    S(r"^\s*(class|module)\s+[A-Z]\w*(::\w+)*(\s*<\s*[\w:]+)?\s*$", 6, 3),
    S(r"^\s*puts\s+\S", 5, 3),
    S(r"\battr_(accessor|reader|writer)\b", 9, 2),
    S(r"^\s*require(_relative)?\s+['\"]", 4, 3),
    S(r"\bdo\s*\|[\w, *]+\|", 7, 3),
    S(r"\.each(_with_index|_with_object)?\s+do\b|\.each\s*\{|\.map\s*\{|\.(times|upto|downto)\s+do\b", 5, 3),
    S(r"(\S\s*@[a-z_]\w*\b(?![.(])|^\s*@[a-z_]\w*\s*(\|\|)?=)", 2.5, 4),
    S(r"\belsif\b", 5, 2),
    S(r"\bunless\b", 5, 2),
    S(r"\bnil\b", 1.5, 3),
    S(r"\bdef\s+initialize\b", 6, 1),
    S(r"\.(nil|empty|include|any|all|zero|is_a|respond_to|key|start_with|end_with)\?", 4, 3),
    S(r"#\{[^}\n]+\}", 4, 3),
    S(r"\brescue\b", 4, 2),
    S(r"^\s*#\s*frozen_string_literal", 8, 1),
    S(r"(?<=[\s(,\[=]):[a-z_]\w*\b", 2, 4),
    S(r"^\s*(p|pp|print)\s+[\"'\w@]|\bgets\b|\.chomp\b|\.to_(s|i|f|a|sym|h)\b", 3, 4),
    S(r"\|\w+(,\s*\w+)*\|", 2, 3),
]

_SWIFT = [
    S(r"^\s*import\s+(Foundation|UIKit|SwiftUI|Combine|AppKit|CoreData|XCTest|CoreGraphics|MapKit|AVFoundation|Darwin|Cocoa)\b", 12, 2),
    S(r"\bfunc\s+\w+\s*(<[^>]*>)?\s*\(", 3, 4),
    S(r"\)\s*->\s*[\w\[\]?<>:,. ]+\s*\{", 2, 3),
    S(r"\b(let|var)\s+\w+\s*:\s*[A-Z]\w*(<[^>]*>)?[?!]?", 4, 5),
    S(r"\bguard\s+(let\s+|var\s+)?[^\n]*\belse\b", 9, 2),
    S(r"\bif\s+(let|var)\s+\w+", 9, 2),
    S(r"^\s*(final\s+)?(class|struct|enum|protocol|actor)\s+\w+(\s*:\s*[\w, <>.]+)?\s*\{", 3, 3),
    S(r"^\s*(public\s+|private\s+|internal\s+|fileprivate\s+|open\s+)?extension\s+\w+", 8, 2),
    S(r"^\s*(public\s+|private\s+)?protocol\s+\w+", 8, 2),
    S(r"@(State|Binding|Published|ObservedObject|IBOutlet|IBAction|main|objc|escaping|StateObject|Environment|EnvironmentObject|MainActor|available|discardableResult)\b", 9, 3),
    S(r"\bsome\s+View\b|\bVStack\b|\bHStack\b", 10, 2),
    S(r"\b(override|final|mutating|convenience)\s+(func|init|var|class)\b", 7, 3),
    S(r"\bnil\b", 1.5, 3),
    S(r"\{\s*(\([\w, :]*\)\s*(->\s*\w+\s*)?|\w+(,\s*\w+)*\s*)in\b", 5, 2),
    S(r"\b(Int|String|Double|Bool|Array|Dictionary|Optional|CGFloat|Float|Void)\b", 1.5, 4),
    S(r"\btry[?!]?\s+\w+|\bcatch\s*\{|\bdo\s*\{", 3, 2),
    S(r"\bcase\s+\.\w+|\bcase\s+let\b", 5, 2),
    S(r"\b(fileprivate|lazy\s+var|willSet|didSet|inout|associatedtype|deinit)\b", 8, 2),
    S(r"\binit\s*\(", 3, 2),
    S(r"\\\(\w[^)\n]*\)", 6, 2),
    S(r"\bself\.\w+", 1, 3),
    S(r"\[(weak|unowned)\s+self\]|\b(weak|unowned)\s+var\b", 8, 2),
]

_KOTLIN = [
    S(r"\bfun\s+(<[^>]*>\s*)?([\w.<>?]+\.)?\w+\s*\(", 8, 4),
    S(r"\b(val|var)\s+\w+\s*(:\s*[\w<>?,. ]+)?\s*(=|by\b)", 3, 5),
    S(r"^\s*package\s+[\w.]+\s*$", 4, 1),
    S(r"^\s*import\s+\w+(\.\w+)+(\.\*)?(\s+as\s+\w+)?\s*$", 3, 4),
    S(r"\bprintln\s*\(", 2, 3),
    S(r"\b(data|sealed|enum|open|abstract|inner|inline|value|annotation)\s+class\b", 8, 2),
    S(r"\bobject\s+\w+", 3, 2),
    S(r"\bwhen\s*(\([^)]*\))?\s*\{", 9, 2),
    S(r"\bcompanion\s+object\b|\blateinit\b|\bby\s+lazy\b|\boverride\s+fun\b|\bsuspend\s+fun\b", 9, 2),
    S(r"\w\?\.\w|\?:\s|!!(\.|\s|$|\))", 4, 3),
    S(r"\b(listOf|mutableListOf|mapOf|mutableMapOf|setOf|arrayListOf|arrayOf|emptyList|hashMapOf)\s*[(<]", 7, 3),
    S(r"\)\s*:\s*[\w<>?,. ]+\s*(\{|=)\s*", 3, 3),
    S(r"\b(Unit|Int|String|Boolean|Double|Long|Any|Nothing)\b", 1, 4),
    S(r"\.(let|also|apply|run|takeIf|forEach|filter|map)\s*\{", 4, 3),
    S(r"\bconstructor\s*\(|\binit\s*\{", 5, 2),
    S(r"::class\b|\bthis@\w+|\breturn@\w+", 6, 2),
]

_SCALA = [
    S(r"\bdef\s+\w+\s*(\[[^\]]*\])?\s*(\([^)]*\)\s*)*(:\s*[\w\[\], =>]+\s*)?=", 5, 4),
    S(r"\bcase\s+class\b|\bcase\s+object\b", 10, 2),
    S(r"\bobject\s+\w+\s*(extends\s+\w+(\s+with\s+\w+)*)?\s*\{", 5, 2),
    S(r"\btrait\s+\w+", 4, 2),
    S(r"\bextends\s+App\b", 10, 1),
    S(r"\bimplicit\b", 6, 2),
    S(r"\bmatch\s*\{", 6, 2),
    S(r"\bcase\s+[\w_(,) ]+(\s+if\s+[^=\n]+)?\s*=>", 5, 3),
    S(r"\b(val|var)\s+\w+\s*(:\s*[\w\[\], ]+)?\s*=", 2, 5),
    S(r"^\s*package\s+[\w.]+\s*$", 2, 1),
    S(r"^\s*import\s+[\w.]+\.(\{[^}]*\}|_|\*)", 5, 3),
    S(r"\b(Option|List|Map|Seq|Set|Vector|Future|Either)\[[\w\[\], ?_]+\]", 4, 3),
    S(r"\b(Some|None)\b", 1.5, 3),
    S(r"\bprintln\s*\(", 2, 3),
    S(r"\.(map|flatMap|filter|foldLeft|foldRight|foreach|collect|getOrElse|zip|toList|toMap)\s*[({]", 2, 4),
    S(r"\bfor\s*[({][^)}]*<-", 7, 2),
    S(r"\b(sealed|final|lazy|override)\s+(trait|class|val|def)\b", 4, 2),
    S(r"\bUnit\b|\bAny\b|\bNil\b", 2, 2),
]

_PERL = [
    S(r"^#!.*\bperl\b", 10, 1),
    S(r"^\s*use\s+(strict|warnings|utf8|feature|v5[\d.]*|constant|parent|base|lib|POSIX|Data::Dumper|List::Util)\b", 10, 3),
    S(r"\bmy\s*\(?\s*[\$@%]\w+", 6, 6),
    S(r"^\s*sub\s+\w+\s*(\([^)]*\))?\s*\{", 7, 3),
    S(r"=~\s*(m|s|tr|y)?\s*[/{!|#]|!~\s*m?/", 6, 3),
    S(r"\$_\b|@_\b|\$\w+\s*[\[{]|\$#\w+", 2, 5),
    S(r"\bforeach\s+(my\s+)?\$\w+\s*\(", 6, 2),
    S(r"->\s*[\[{]", 3, 3),
    S(r"\b(print|printf)\s+(STDERR|STDOUT|\$\w+|[\"'])", 1.5, 3),
    S(r"(?<![\w.>$@%])\b(open|close|chomp|chop|shift|unshift|push|pop|splice|keys|values|exists|defined|die|warn|sprintf|join|split|bless|ref|wantarray|lc|uc|ucfirst|lcfirst)\b\s*[\(\$@%'\"]", 1.5, 5),
    S(r"\bqw\s*[(/\[{]", 7, 2),
    S(r"@\w+\s*=\s*\(|%\w+\s*=\s*\(", 4, 3),
    S(r"^__(END|DATA)__\s*$|^1;\s*$", 5, 1),
    S(r"^\s*package\s+[\w:]+\s*;", 4, 1),
    S(r"<STDIN>|<\$\w+>", 6, 2),
    S(r"\$\w+\s*(=~|\.=|\|\|=|//=)", 3, 3),
    S(r"[\$@%]\w+", 0.8, 8),
]

_LUA = [
    S(r"^#!.*\blua\b", 10, 1),
    S(r"\blocal\s+(function\s+)?\w+", 5, 6),
    S(r"\bfunction\s+[\w.:]+\s*\(", 2, 3),
    S(r"\bthen\b", 3, 4),
    S(r"\belseif\b", 6, 2),
    S(r"^\s*end\s*[,)]*\s*$", 2, 6),
    S(r"~=", 6, 2),
    S(r"\b(ipairs|pairs)\s*\(", 6, 3),
    S(r"\s\.\.\s", 4, 3),
    S(r"\b(table|string|math|os|io)\.(insert|remove|concat|sort|format|sub|gsub|find|len|upper|lower|floor|ceil|random|sqrt|max|min|time|date|read|write|open)\s*\(", 6, 4),
    S(r"\brepeat\s*$[\s\S]*?^\s*until\b", 8, 1),
    S(r"\bfor\s+\w+\s*=\s*[^,\n]+,[^\n]+\bdo\b|\bfor\s+\w+(\s*,\s*\w+)?\s+in\s+(i?pairs|next)\b[^\n]*\bdo\b", 8, 2),
    S(r"\bwhile\s+[^\n]+\s+do\s*$", 3, 2),
    S(r"\bsetmetatable\s*\(", 6, 2),
    S(r"\bnil\b", 2, 3),
    S(r"^\s*--(?!\[)", 1, 3),
    S(r"\blocal\s+\w+\s*=\s*require\b", 8, 1),
    S(r"\bfunction\s*\([^)]*\)\s*$", 3, 2),
]

_R = [
    S(r"[\w.\]\)]\s*<-\s*\S", 6, 6),
    S(r"\b(library|require|suppressPackageStartupMessages)\s*\(\s*\w+\s*\)", 7, 3),
    S(r"%>%|\|>|%in%|%\*%|%o%", 8, 2),
    S(r"\b(data\.frame|ggplot|aes|tibble|mutate|summarise|summarize|group_by|geom_\w+|read\.csv|read_csv|write\.csv|setwd|set\.seed|rnorm|runif|lapply|sapply|vapply|mapply|seq_along|seq_len|nrow|ncol|colnames|rownames|rbind|cbind|paste0?|is\.na|is\.null|tapply)\s*\(", 3, 6),
    S(r"\b(TRUE|FALSE|NULL|NA|NA_integer_|NA_character_|Inf)\b", 2, 4),
    S(r"\bc\s*\(", 1.5, 3),
    S(r"\bfunction\s*\([^)]*\)\s*\{", 1, 2),
    S(r"\[\[[^\]]+\]\]", 2, 3),
    S(r"\bfor\s*\(\s*\w+\s+in\s+[^)]+\)\s*\{", 2, 3),
    S(r"\w\$\w+", 2, 4),
]

_SHELL = [
    S(r"^#!.*\b(ba|z|k|da|a)?sh\b", 10, 1),
    S(r"^\s*(if|elif|while|until)\s+\[\[?\s", 6, 4),
    S(r"\[\[?\s+[^\]\n]*\s+\]\]?", 3, 4),
    S(r"^\s*(fi|done|esac)\s*(;|$)", 6, 4),
    S(r"\bthen\s*$", 2, 3),
    S(r"\$\{?[A-Za-z_]\w*\}?", 1.5, 6),
    S(r"\$\(\s*[^)\n]+\)", 3, 3),
    S(r"^\s*export\s+[A-Za-z_]\w*=", 6, 2),
    S(r"^\s*(local\s+|readonly\s+|declare\s+(-\w+\s+)?)?[A-Za-z_]\w*=[^=\s]", 3, 5),
    S(r"^\s*(sudo\s+)?(grep|awk|sed|cut|sort|uniq|xargs|find|chmod|chown|mkdir|rm|cp|mv|cat|curl|wget|tar|ls|cd|source|kill|ps|tail|head|touch|ln|ssh|scp|rsync|echo|printf|wc|tee|tr|diff|du|df)\s+[-$./~'\"*]", 3, 8),
    S(r"^\s*(sudo\s+)?(apt(-get)?|yum|dnf|brew|pip3?|npm|git|docker|systemctl)\s+[a-z-]+", 3, 4),
    S(r"\|\s*(grep|awk|sed|sort|uniq|head|tail|wc|cut|tr|xargs|tee|less|jq)\b", 5, 3),
    S(r"^\s*for\s+\w+\s+in\s+[^\n]*;\s*do\b|^\s*do\s*$", 7, 2),
    S(r"^\s*while\s+(true|:|read\b|\[)", 3, 2),
    S(r"^\s*(function\s+\w+\s*(\(\s*\))?\s*\{|\w+\s*\(\s*\)\s*\{)", 5, 3),
    S(r"\b2>&1|>\s*/dev/null|&>\s*\S|>>\s*\S+", 4, 3),
    S(r"^\s*case\s+.+\s+in\s*$", 6, 2),
    S(r"\$[0-9@#?*!]", 3, 3),
    S(r"^\s*set\s+-[euxo]+", 6, 1),
    S(r"\$\{[^}]*(:-|:=|:\+|##|%%|//)[^}]*\}", 5, 2),
    S(r"\[\s+-[fdezrwxnsLh]\s+", 5, 3),
    S(r"^\s*(trap|exec|shift|eval|wait|getopts)\b", 3, 2),
    S(r"\bread\s+-[rps]+", 5, 2),
    S(r";;\s*$", 5, 3),
]

_POWERSHELL = [
    S(r"\b(Get|Set|New|Remove|Write|Invoke|Import|Export|Add|Test|Start|Stop|Out|Select|Where|ForEach|Format|ConvertTo|ConvertFrom|Read|Copy|Move|Rename|Clear|Install|Enable|Disable|Join|Split|Measure|Sort|Compare)-[A-Z][A-Za-z]+", 8, 5),
    S(r"\bparam\s*\(", 7, 1),
    S(r"\[(string|int|bool|switch|array|hashtable|PSCustomObject|datetime|void|object|CmdletBinding|Parameter|ValidateSet|System\.\w+)\b[^\]]*\]", 6, 4),
    S(r"\$(_|PSScriptRoot|PSItem|true|false|null|env:\w+|args|Error|PWD|Host)\b", 5, 4),
    S(r"\s-(eq|ne|gt|lt|ge|le|like|notlike|match|notmatch|contains|notcontains|and|or|not|in|is|as|replace|split|join|f)\b", 6, 5),
    S(r"\|\s*(Where-Object|ForEach-Object|Select-Object|Sort-Object|Out-\w+|Format-\w+|%|\?)", 5, 3),
    S(r"\s-(Path|Name|Force|Recurse|ErrorAction|Value|ItemType|Filter|Verbose|Destination|Include|Exclude|ComputerName|Credential|Object|InputObject)\b", 5, 5),
    S(r"@\{|@\(", 4, 3),
    S(r"\bforeach\s*\(\s*\$\w+\s+in\b", 7, 2),
    S(r"^\s*(<#|#>|#requires)", 6, 2),
    S(r"\$\w+\s*=\s*", 1.5, 5),
    S(r"\bfunction\s+[\w-]+\s*(\([^)]*\))?\s*\{", 2, 3),
    S(r"::\w+\(|\[System\.", 3, 2),
]

_SQL = [
    S(r"\bSELECT\b[\s\S]{0,400}?\bFROM\b", 7, 5, re.I),
    S(r"\b(INSERT\s+INTO|UPDATE\s+\w+(\.\w+)?\s+SET|DELETE\s+FROM)\b", 7, 4, re.I),
    S(r"\bCREATE\s+(OR\s+REPLACE\s+)?(TEMP(ORARY)?\s+)?(TABLE|VIEW|INDEX|UNIQUE\s+INDEX|DATABASE|PROCEDURE|FUNCTION|TRIGGER|SCHEMA)\b", 8, 4, re.I),
    S(r"\b(ALTER\s+TABLE|DROP\s+(TABLE|VIEW|INDEX|DATABASE|SCHEMA)|TRUNCATE\s+TABLE)\b", 8, 3, re.I),
    S(r"\b(GROUP\s+BY|ORDER\s+BY|HAVING|UNION(\s+ALL)?|DISTINCT)\b", 3, 6),
    S(r"\b(group|order)\s+by\b", 3, 3),
    S(r"\b(INNER|LEFT|RIGHT|FULL|CROSS)\s+(OUTER\s+)?JOIN\b", 7, 4, re.I),
    S(r"\bJOIN\s+\w+(\.\w+)?(\s+(AS\s+)?\w+)?\s+ON\b", 5, 3, re.I),
    S(r"\b(PRIMARY\s+KEY|FOREIGN\s+KEY|REFERENCES\s+\w+|NOT\s+NULL|AUTO_INCREMENT|AUTOINCREMENT|VARCHAR|NVARCHAR|TIMESTAMP|SERIAL|BIGINT|DEFAULT\s+\w+|CONSTRAINT)\b", 3, 6),
    S(r"\b(COUNT|SUM|AVG|MIN|MAX|COALESCE|NOW|CAST|ROW_NUMBER|CURRENT_TIMESTAMP)\s*\(", 2, 4),
    S(r"^\s*--", 1, 3),
    S(r"\bVALUES\s*\(", 5, 3, re.I),
    S(r"\b(BEGIN|COMMIT|ROLLBACK|DECLARE|TRANSACTION)\b", 1.5, 3),
    S(r"\b(IN|EXISTS)\s*\(\s*SELECT\b", 5, 2, re.I),
    S(r"\bWHERE\b[^\n]*(=|<|>|\bLIKE\b|\bIN\b|\bIS\s+(NOT\s+)?NULL\b)", 4, 4),
]

_HASKELL = [
    S(r"^module\s+[\w.]+(\s*\([^)]*\))?\s+where\b", 10, 1),
    S(r"^import\s+(qualified\s+)?[A-Z][\w.]*(\s+(as\s+[A-Z]\w*|hiding\s*\(.*\)|\(.*\)))?\s*$", 6, 4),
    S(r"^[a-z_][\w']*\s+::\s+[A-Za-z(\[][^=\n]*$", 7, 5),
    S(r"^data\s+[A-Z]\w*[^=\n]*=|^newtype\s+[A-Z]|^instance\s+[A-Z]|^class\s+\(?[A-Z]\w*\)?\s+.*\bwhere\b", 6, 3),
    S(r"\bderiving\s*\(?", 7, 2),
    S(r"\b(mapM_?|forM_?|putStrLn|putStr|getLine|fmap|foldr|foldl|zipWith|concatMap)\b", 2, 5),
    S(r"\bIO\s*(\(\)|[A-Z]\w*)", 7, 2),
    S(r"\bwhere\s*$|\blet\b[^\n]*\bin\b|\bcase\s+\w+\s+of\b", 4, 3),
    S(r"^\s*main\s*=\s*do\b", 6, 1),
    S(r">>=|<\$>|<\*>", 4, 3),
    S(r"\{-|-\}", 4, 2),
    S(r"\(\w+:\w+s?\)", 5, 3),
]

_ASM = [
    S(r"^\s*section\s+\.(text|data|bss|rodata)|^\s*\.(text|data|bss|globl|global|section|align|byte|word|long|quad|ascii|asciz)\b", 7, 4),
    S(r"^\s*(global|extern)\s+\w+", 4, 2),
    S(r"^\s*(mov\w*|add|sub|xor|cmp|lea|imul|shl|shr|ldr|str|test)\s+[\w\[\]%$.+\-*]+\s*,\s*[\w\[\]%$.+\-* ]+", 4, 12),
    S(r"^\s*(push|pop|call|jmp|je|jne|jz|jnz|jg|jl|jge|jle|ja|jb|inc|dec|idiv|mul|div)\s+[\w%$.\[\]]+\s*(;.*)?$", 4, 8),
    S(r"^\s*(ret|leave|nop|syscall|cdq|cqo)\s*(;.*)?$", 4, 3),
    S(r"\b(eax|ebx|ecx|edx|esi|edi|esp|ebp|rax|rbx|rcx|rdx|rsi|rdi|rsp|rbp|r(8|9|1[0-5])d?|xmm[0-9]+)\b", 3, 6),
    S(r"^\s*[_.][\w.]*:\s*(;.*)?$", 3, 4),
    S(r"\s(db|dw|dd|dq|equ|resb|resw|resd)\s+\S", 4, 3),
    S(r"^\s*int\s+0x[0-9a-fA-F]+\s*(;.*)?$", 5, 2),
]

_MAKEFILE = [
    S(r"^\.PHONY\b", 10, 1),
    S(r"\$\([A-Z_][A-Z0-9_]*\)", 3, 5),
    S(r"\$[@<^](?![\w{(])", 3, 3),
    S(r"^%\.\w+\s*:\s*%\.\w+|^\w[\w./-]*\.o\s*:", 8, 2),
    S(r"^[\w.%/$()@-]+(\s+[\w.%/$()@-]+)*\s*:(?!=)[^=\n#]*\n\t+\S", 5, 4),
    S(r"^[A-Z][A-Z0-9_]*\s*[:?+]?=\s*\S", 2, 4),
    S(r"^(-?include|ifeq|ifneq|ifdef|ifndef|endif)\b", 3, 3),
]


# Terraform / HCL.  The block-header signatures ("resource "x" "y" {") are very
# specific; the weaker ones only add up when several of them appear together.
_TERRAFORM = [
    S(r'^\s*terraform\s*\{', 10, 1),
    S(r'^\s*resource\s+"[\w-]+"\s+"[\w-]+"\s*\{', 12, 3),
    S(r'^\s*data\s+"[\w-]+"\s+"[\w-]+"\s*\{', 10, 3),
    S(r'^\s*provider\s+"[\w-]+"\s*\{', 8, 2),
    S(r'^\s*variable\s+"[\w-]+"\s*\{', 8, 3),
    S(r'^\s*output\s+"[\w-]+"\s*\{', 8, 3),
    S(r'^\s*module\s+"[\w-]+"\s*\{', 8, 2),
    S(r'^\s*locals\s*\{', 6, 1),
    S(r'\brequired_(providers|version)\b', 6, 2),
    S(r'^\s*(lifecycle|provisioner\s+"[\w-]+"|dynamic\s+"[\w-]+"|backend\s+"[\w-]+")\s*\{', 4, 2),
    S(r'\b(var|local)\.[a-z_]\w*', 2, 3),
    S(r'^\s*(count|for_each|depends_on)\s*=', 2, 2),
]


# Keys are tree_sitter_language_pack names.  Order matters for ties: the earlier
# language wins (javascript before typescript, c before cpp, ...).
SIGNATURES: Dict[str, List[Sig]] = {
    "python": _PYTHON,
    "javascript": _JS,
    "typescript": _JS + _TS_EXTRA,          # superset of JavaScript
    "java": _JAVA,
    "c": _C,
    "cpp": _C + _CPP_EXTRA,                 # superset of C
    "csharp": _CSHARP,
    "go": _GO,
    "rust": _RUST,
    "php": _PHP,
    "ruby": _RUBY,
    "swift": _SWIFT,
    "kotlin": _KOTLIN,
    "scala": _SCALA,
    "perl": _PERL,
    "lua": _LUA,
    "r": _R,
    "bash": _SHELL,
    "powershell": _POWERSHELL,
    "sql": _SQL,
    "haskell": _HASKELL,
    "asm": _ASM,
    "make": _MAKEFILE,
    "terraform": _TERRAFORM,
}
