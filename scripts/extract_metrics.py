#!/usr/bin/env python3
"""
QMOOD metric extractor for Java source trees.

Extracts class-level OO metrics (CK + Li&Henry + QMOOD/Bansiya-Davis sets)
from Java source code using the `javalang` parser (no compilation needed),
then aggregates them into the 11 QMOOD design properties at system level.

Per-class metrics:
  NOA, NOM, CIS, DAM, WMC, RFC, CBO, DCC, MPC, DAC/MOA, LCOM(1), CAM,
  DIT, NOC, ANA, MFA, NOP
System level: DSC (design size), NOH (number of hierarchies)

Notes / approximations (document these in the report!):
  * Coupling counts only project-internal classes (same convention as
    Bansiya & Davis' QMOOD tool, which analyses the system itself).
  * DIT/ANA are computed over the project-internal inheritance tree;
    external superclasses (e.g. JDK classes) count as depth 0 extra.
  * NOP = abstract methods + methods overriding a project ancestor method
    (signature = name + arity). Annotation-independent, so it is
    comparable across old (pre-@Override) and new versions.
  * MPC is a static approximation: calls whose receiver's declared type
    (field/param/local) resolves to another project class.
  * Test code is excluded by analysing only the main source root.
"""
import os
import sys
import csv
import json
import javalang
from javalang import tree as T
from collections import defaultdict

PRIMITIVES = {"int", "long", "short", "byte", "float", "double", "boolean", "char", "void", "var"}
DECISION_NODES = (T.IfStatement, T.WhileStatement, T.DoStatement, T.ForStatement,
                  T.CatchClause, T.TernaryExpression)


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def type_names(t):
    """All reference-type simple names mentioned in a type (incl. generics)."""
    out = []
    if t is None or isinstance(t, T.BasicType):
        return out
    if isinstance(t, T.ReferenceType):
        if t.name:
            out.append(t.name)
        for a in (t.arguments or []):
            if a is not None and getattr(a, "type", None) is not None:
                out += type_names(a.type)
        if t.sub_type is not None:
            out += type_names(t.sub_type)
    return out


def iter_sub(node):
    """Iterate all sub-nodes of a javalang node (or list of nodes)."""
    if node is None:
        return
    items = node if isinstance(node, (list, tuple)) else [node]
    for it in items:
        if isinstance(it, javalang.ast.Node):
            for path, n in it.filter(javalang.ast.Node):
                yield n
        elif isinstance(it, (list, tuple)):
            yield from iter_sub(it)


def analyze_callable(m):
    """Extract body-level facts from a MethodDeclaration / ConstructorDeclaration."""
    cc = 0
    invocations = []      # (qualifier, member)
    created = []          # instantiated type names
    localvars = {}        # name -> simple type name
    raw_members = set()   # unqualified / this-qualified member references
    for n in iter_sub(m.body):
        if isinstance(n, DECISION_NODES):
            cc += 1
        elif isinstance(n, T.SwitchStatementCase):
            cc += max(1, len(n.case or []))
        elif isinstance(n, T.BinaryOperation) and n.operator in ("&&", "||"):
            cc += 1
        if isinstance(n, T.MethodInvocation):
            invocations.append((n.qualifier, n.member))
        elif isinstance(n, T.SuperMethodInvocation):
            invocations.append(("super", n.member))
        elif isinstance(n, T.ClassCreator):
            created += type_names(n.type)
        elif isinstance(n, T.LocalVariableDeclaration):
            tn = type_names(n.type)
            for d in n.declarators:
                if tn:
                    localvars[d.name] = tn[0]
        elif isinstance(n, T.MemberReference):
            if n.qualifier in (None, "", "this"):
                raw_members.add(n.member)
        elif isinstance(n, T.This):
            sel = n.selectors or []
            if sel and isinstance(sel[0], T.MemberReference):
                raw_members.add(sel[0].member)
    params = {}
    for p in (m.parameters or []):
        tn = type_names(p.type)
        params[p.name] = tn[0] if tn else None
    return {
        "name": getattr(m, "name", "<init>"),
        "arity": len(m.parameters or []),
        "public": "public" in m.modifiers,
        "static": "static" in m.modifiers,
        "abstract": "abstract" in m.modifiers,
        "override_anno": any(a.name == "Override" for a in (m.annotations or [])),
        "param_types": [t for p in (m.parameters or []) for t in type_names(p.type)],
        "param_type_set": sorted({type_names(p.type)[0] for p in (m.parameters or []) if type_names(p.type)}
                                 | {p.type.name for p in (m.parameters or []) if isinstance(p.type, T.BasicType)}),
        "return_types": type_names(getattr(m, "return_type", None)),
        "cc": cc,
        "invocations": invocations,
        "created": created,
        "localvars": localvars,
        "params": params,
        "raw_members": sorted(raw_members),
    }


def members_of(node):
    """Direct (non-nested) fields / methods / constructors of a type declaration."""
    if isinstance(node, T.EnumDeclaration):
        decls = list(node.body.declarations or [])
    else:
        decls = list(node.body or [])
    fields = [d for d in decls if isinstance(d, T.FieldDeclaration)]
    methods = [d for d in decls if isinstance(d, T.MethodDeclaration)]
    ctors = [d for d in decls if isinstance(d, T.ConstructorDeclaration)]
    return fields, methods, ctors


# ----------------------------------------------------------------------------
# pass 1: parse files -> plain dict records
# ----------------------------------------------------------------------------
def parse_file(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        src = fh.read()
    cu = javalang.parse.parse(src)
    pkg = cu.package.name if cu.package else ""
    imports = [(i.path, bool(i.wildcard), bool(i.static)) for i in cu.imports]
    records = []
    for tpath, node in cu.filter(T.TypeDeclaration):
        if isinstance(node, T.AnnotationDeclaration):
            continue
        outers = [n.name for n in tpath if isinstance(n, T.TypeDeclaration)]
        fqn = ".".join(([pkg] if pkg else []) + outers + [node.name])
        kind = ("interface" if isinstance(node, T.InterfaceDeclaration)
                else "enum" if isinstance(node, T.EnumDeclaration) else "class")
        ext = []
        if isinstance(node, T.ClassDeclaration) and node.extends is not None:
            ext = type_names(node.extends)[:1]
        elif isinstance(node, T.InterfaceDeclaration) and node.extends:
            for e in node.extends:
                ext += type_names(e)[:1]
        impl = []
        for i in (getattr(node, "implements", None) or []):
            impl += type_names(i)[:1]
        fields, methods, ctors = members_of(node)
        frecs = []
        for f in fields:
            vis = ("private" if "private" in f.modifiers
                   else "protected" if "protected" in f.modifiers
                   else "public" if "public" in f.modifiers else "package")
            tn = type_names(f.type)
            for d in f.declarators:
                frecs.append({"name": d.name, "types": tn, "vis": vis,
                              "static": "static" in f.modifiers})
        records.append({
            "fqn": fqn, "simple": node.name, "pkg": pkg, "kind": kind,
            "abstract": "abstract" in (node.modifiers or set()),
            "extends": ext, "implements": impl,
            "fields": frecs,
            "methods": [analyze_callable(m) for m in methods],
            "ctors": [analyze_callable(c) for c in ctors],
            "imports": imports,
        })
    return records


def collect_sources(src_root):
    out = []
    for base, _dirs, files in os.walk(src_root):
        for f in files:
            if f.endswith(".java") and f != "package-info.java":
                out.append(os.path.join(base, f))
    return sorted(out)


# ----------------------------------------------------------------------------
# pass 2: resolve project-internal references + compute metrics
# ----------------------------------------------------------------------------
def make_resolver(pkg, imports, fqns, registry):
    explicit = {p.rsplit(".", 1)[-1]: p for (p, wild, stat) in imports if not wild and not stat}
    wildcards = [p for (p, wild, stat) in imports if wild and not stat]

    def resolve(simple):
        if not simple or simple in PRIMITIVES or not simple[0].isupper():
            return None
        if simple in explicit:
            p = explicit[simple]
            return p if p in fqns else None
        cand = f"{pkg}.{simple}" if pkg else simple
        if cand in fqns:
            return cand
        for w in wildcards:
            if f"{w}.{simple}" in fqns:
                return f"{w}.{simple}"
        s = registry.get(simple)
        if s and len(s) == 1:
            return next(iter(s))
        return None
    return resolve


def compute_metrics(classes):
    fqns = {c["fqn"] for c in classes}
    registry = defaultdict(set)
    for c in classes:
        registry[c["simple"]].add(c["fqn"])
    by_fqn = {c["fqn"]: c for c in classes}

    # resolve inheritance (extends only -> class hierarchy)
    parent, children = {}, defaultdict(list)
    for c in classes:
        r = make_resolver(c["pkg"], c["imports"], fqns, registry)
        c["_resolve"] = r
        if c["extends"]:
            p = r(c["extends"][0])
            if p and p != c["fqn"]:
                parent[c["fqn"]] = p
                children[p].append(c["fqn"])

    def ancestors(fqn):
        out, seen = [], {fqn}
        cur = parent.get(fqn)
        while cur and cur not in seen:
            out.append(cur)
            seen.add(cur)
            cur = parent.get(cur)
        return out

    declared_sigs = {c["fqn"]: {(m["name"], m["arity"]) for m in c["methods"]} for c in classes}
    inheritable = {c["fqn"]: {(m["name"], m["arity"]) for m in c["methods"]
                              if not m["static"]} for c in classes}

    rows = []
    for c in classes:
        r = c["_resolve"]
        fqn = c["fqn"]
        anc = ancestors(fqn)
        field_names = {f["name"] for f in c["fields"]}
        own_sigs = declared_sigs[fqn]
        inherited = set()
        for a in anc:
            inherited |= inheritable.get(a, set())
        inherited -= own_sigs
        anc_sig_pool = set().union(*(inheritable.get(a, set()) for a in anc)) if anc else set()

        methods, ctors = c["methods"], c["ctors"]
        NOM, NOA = len(methods), len(c["fields"])
        CIS = sum(1 for m in methods if m["public"])
        hidden = sum(1 for f in c["fields"] if f["vis"] in ("private", "protected"))
        DAM = (hidden / NOA) if NOA else None
        WMC = sum(1 + m["cc"] for m in methods + ctors)

        # --- coupling sets -------------------------------------------------
        def resolve_all(names):
            out = set()
            for n in names:
                p = r(n)
                if p and p != fqn:
                    out.add(p)
            return out

        field_types = [t for f in c["fields"] for t in f["types"]]
        param_types = [t for m in methods + ctors for t in m["param_types"]]
        ret_types = [t for m in methods for t in m["return_types"]]
        created = [t for m in methods + ctors for t in m["created"]]
        local_types = [t for m in methods + ctors for t in m["localvars"].values()]

        dcc_set = resolve_all(field_types) | resolve_all(param_types)
        cbo_set = (dcc_set | resolve_all(ret_types) | resolve_all(created)
                   | resolve_all(local_types) | resolve_all(c["extends"])
                   | resolve_all(c["implements"]))

        DAC = sum(1 for f in c["fields"] if any(r(t) and r(t) != fqn for t in f["types"]))

        # --- messaging (MPC) + RFC + CBO via call receivers ---------------
        MPC = 0
        invoked_names = set()
        ftype = {f["name"]: (f["types"][0] if f["types"] else None) for f in c["fields"]}
        for m in methods + ctors:
            scope = dict(ftype)
            scope.update(m["params"])
            scope.update(m["localvars"])
            for q, member in m["invocations"]:
                invoked_names.add(member)
                if q in (None, "", "this", "super"):
                    continue
                head = q.split(".")[0]
                if head == "this" and "." in q:
                    head = q.split(".")[1]
                tname = scope.get(head)
                target = r(tname) if tname else r(head)  # variable type or static call
                if target and target != fqn:
                    MPC += 1
                    cbo_set.add(target)
        RFC = NOM + len(invoked_names)
        CBO, DCC = len(cbo_set), len(dcc_set)

        # --- cohesion ------------------------------------------------------
        msets = []
        for m in methods:
            shadow = set(m["params"]) | set(m["localvars"])
            msets.append({x for x in m["raw_members"] if x in field_names and x not in shadow})
        P = Q = 0
        for i in range(len(msets)):
            for j in range(i + 1, len(msets)):
                if msets[i] & msets[j]:
                    Q += 1
                else:
                    P += 1
        LCOM = max(P - Q, 0)
        pt_union = set().union(*(set(m["param_type_set"]) for m in methods)) if methods else set()
        CAM = (sum(len(set(m["param_type_set"])) for m in methods) / (NOM * len(pt_union))
               if NOM and pt_union else None)

        # --- inheritance / polymorphism ------------------------------------
        ANA = len(anc)
        DIT = ANA + 1
        NOC = len(children.get(fqn, []))
        denom = len(inherited) + NOM
        MFA = (len(inherited) / denom) if denom else 0.0
        # NOP_strict: annotation-independent (abstract or overrides a project
        # ancestor). Comparable across pre/post-@Override-era code.
        # NOP: additionally counts @Override methods (incl. overrides of
        # external/JDK types) -- inflated after mass annotation adoption.
        poly_strict = [m["abstract"] or (m["name"], m["arity"]) in anc_sig_pool
                       for m in methods]
        NOP_strict = sum(poly_strict)
        NOP = sum(1 for m, s in zip(methods, poly_strict) if s or m["override_anno"])

        rows.append({
            "class": fqn, "kind": c["kind"], "abstract": int(c["abstract"]),
            "NOA": NOA, "NOM": NOM, "CIS": CIS,
            "DAM": round(DAM, 4) if DAM is not None else "",
            "WMC": WMC, "RFC": RFC, "CBO": CBO, "DCC": DCC, "MPC": MPC,
            "DAC": DAC, "MOA": DAC, "LCOM": LCOM,
            "CAM": round(CAM, 4) if CAM is not None else "",
            "DIT": DIT, "NOC": NOC, "ANA": ANA,
            "MFA": round(MFA, 4), "NOP": NOP, "NOP_strict": NOP_strict,
        })
        c.pop("_resolve", None)

    # ---- system-level aggregation ------------------------------------------
    cls_rows = [r_ for r_, c in zip(rows, classes) if c["kind"] in ("class", "enum")]
    n_int = sum(1 for c in classes if c["kind"] == "interface")

    def mean(key, skip_blank=False):
        vals = [r_[key] for r_ in cls_rows if not (skip_blank and r_[key] == "")]
        return sum(float(v) for v in vals) / len(vals) if vals else 0.0

    DSC = len(cls_rows)
    roots = [c["fqn"] for c in classes if c["kind"] in ("class", "enum")
             and c["fqn"] not in parent and children.get(c["fqn"])]
    NOH = len(roots)

    properties = {
        "DesignSize": DSC,                    # DSC
        "Hierarchies": NOH,                   # NOH
        "Abstraction": mean("ANA"),           # ANA
        "Encapsulation": mean("DAM", True),   # DAM
        "Coupling": mean("DCC"),              # DCC
        "Cohesion": mean("CAM", True),        # CAM
        "Composition": mean("MOA"),           # MOA
        "Inheritance": mean("MFA"),           # MFA
        "Polymorphism": mean("NOP_strict"),   # NOP (annotation-independent)
        "Messaging": mean("CIS"),             # CIS
        "Complexity": mean("NOM"),            # NOM
    }
    raw_means = {k: mean(k) for k in ("WMC", "CBO", "RFC", "LCOM", "DIT", "NOC",
                                      "NOM", "NOA", "MPC", "DAC")}
    return rows, properties, raw_means, {"n_classes": DSC, "n_interfaces": n_int}


# ----------------------------------------------------------------------------
def analyze_tree(src_root, label, outdir):
    files = collect_sources(src_root)
    classes, failed = [], []
    for fp in files:
        try:
            classes += parse_file(fp)
        except Exception as e:
            failed.append((fp, str(e)[:120]))
    rows, props, raw, counts = compute_metrics(classes)
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "classes.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    summary = {"version": label, "n_files": len(files), "n_parse_failed": len(failed),
               **counts, "properties": props, "raw_means": raw,
               "failed_files": [f for f, _ in failed][:20]}
    with open(os.path.join(outdir, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    return summary


if __name__ == "__main__":
    src_root, label, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    s = analyze_tree(src_root, label, outdir)
    print(json.dumps({k: s[k] for k in ("version", "n_files", "n_parse_failed", "n_classes")},
                     indent=None))
