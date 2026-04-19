import os
import re
from typing import Any, Dict, List, Optional, Sequence, Union

# Keep in sync with frontend/src/config/athenaAllowlist.ts and
# data/schemas/calcofi_schema.sql (bottle_table only; cast_table has different columns).
ALLOWED_COLUMNS: frozenset[str] = frozenset(
    {
        "cst_cnt",
        "btl_cnt",
        "sta_id",
        "depth_id",
        "depthm",
        "t_degc",
        "salnty",
        "o2ml_l",
        "stheta",
        "o2sat",
        "oxy_umol_kg",
        "recind",
        "t_prec",
        "s_prec",
        "p_qual",
        "chlqua",
        "phaqua",
        "po4um",
        "po4q",
        "sio3um",
        "sio3qu",
        "no2um",
        "no2q",
        "no3um",
        "no3q",
        "nh3q",
        "c14a1q",
        "c14a2q",
        "darkaq",
        "meanaq",
        "r_depth",
        "r_temp",
        "r_sal",
        "r_dynht",
        "r_oxy_umol_kg",
    }
)

ALLOWED_OPS: frozenset[str] = frozenset({"=", "!=", "<", "<=", ">", ">=", "BETWEEN"})

IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

DEFAULT_LIMIT = 10
MAX_LIMIT = 500


def _assert_table_name(name: str) -> str:
    if not isinstance(name, str) or not IDENT_RE.match(name):
        raise ValueError("Invalid ATHENA_TABLE name in environment")
    return name


def _assert_column(name: str) -> str:
    if not isinstance(name, str):
        raise ValueError(f"Invalid column identifier: {name!r}")
    raw = name.strip()
    if not raw or not IDENT_RE.match(raw):
        raise ValueError(f"Invalid column identifier: {name!r}")
    # Athena / Glue unquoted identifiers are case-insensitive; JSON may send mixed case.
    normalized = raw.lower()
    if normalized not in ALLOWED_COLUMNS:
        raise ValueError(f"Unknown or disallowed column: {name!r}")
    return normalized


def _assert_iso_date(s: str, field: str) -> str:
    if not isinstance(s, str) or not ISO_DATE_RE.fullmatch(s):
        raise ValueError(f"{field} must be YYYY-MM-DD")
    return s


def _coerce_number(val: Any) -> Union[int, float]:
    if isinstance(val, bool):
        raise ValueError("Boolean is not a valid numeric value")
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        if val != val or val in (float("inf"), float("-inf")):
            raise ValueError("Invalid numeric value")
        return val
    if isinstance(val, str):
        t = val.strip()
        if not t:
            raise ValueError("Empty numeric string")
        try:
            if any(c in t for c in ".eE"):
                x = float(t)
                if x != x or x in (float("inf"), float("-inf")):
                    raise ValueError("Invalid numeric value")
                return x
            return int(t, 10)
        except ValueError as e:
            raise ValueError(f"Not a number: {val!r}") from e
    raise ValueError(f"Unsupported numeric type: {type(val).__name__}")


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        raise ValueError("Boolean values are not supported in filters")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("Invalid numeric value")
        return repr(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            raise ValueError("Empty string value")
        if ISO_DATE_RE.fullmatch(s):
            return "'" + s.replace("'", "''") + "'"
        try:
            n = _coerce_number(s)
            return str(n) if isinstance(n, int) else repr(n)
        except ValueError:
            pass
        if len(s) > 256:
            raise ValueError("String value too long")
        if re.fullmatch(r"[A-Za-z0-9_.\-:]+", s):
            return "'" + s.replace("'", "''") + "'"
        raise ValueError(f"Unsupported string value: {value!r}")
    raise ValueError(f"Unsupported value type: {type(value).__name__}")


def _one_predicate(column: str, op: str, value: Any) -> str:
    col_sql = _assert_column(column)
    if op not in ALLOWED_OPS:
        raise ValueError(f"Unsupported operator: {op!r}")
    if op == "BETWEEN":
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError("BETWEEN requires value as a two-element array [low, high]")
        lo, hi = value[0], value[1]
        return f"{col_sql} BETWEEN {_format_scalar(lo)} AND {_format_scalar(hi)}"
    return f"{col_sql} {op} {_format_scalar(value)}"


def _parse_limit(raw: Any) -> int:
    if raw is None:
        return DEFAULT_LIMIT
    if isinstance(raw, bool):
        raise ValueError("limit must be an integer")
    if isinstance(raw, int):
        lim = raw
    elif isinstance(raw, float) and raw == int(raw):
        lim = int(raw)
    else:
        raise ValueError("limit must be an integer")
    if lim < 1 or lim > MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
    return lim


def _normalize_order_by(raw: Any) -> Optional[Dict[str, str]]:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("orderBy must be an object with column and optional direction")
    col = raw.get("column")
    if not isinstance(col, str) or not col:
        raise ValueError("orderBy.column is required")
    _assert_column(col)
    direction = raw.get("direction", "ASC")
    if not isinstance(direction, str):
        raise ValueError("orderBy.direction must be a string")
    direction = direction.upper()
    if direction not in ("ASC", "DESC"):
        raise ValueError("orderBy.direction must be ASC or DESC")
    return {"column": col, "direction": direction}


def _normalize_filters(raw: Any) -> List[Dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("filters must be an array")
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"filters[{i}] must be an object")
        col = item.get("column")
        op = item.get("op")
        val = item.get("value")
        if not isinstance(col, str) or not isinstance(op, str):
            raise ValueError(f"filters[{i}] requires string column and op")
        out.append({"column": col, "op": op, "value": val})
    return out


def _normalize_columns(raw: Any) -> Optional[List[str]]:
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ValueError("columns must be an array of strings or omitted for SELECT *")
    if len(raw) == 0:
        return None
    seen: set[str] = set()
    out: List[str] = []
    for i, c in enumerate(raw):
        if not isinstance(c, str):
            raise ValueError(f"columns[{i}] must be a string")
        ac = _assert_column(c)
        if ac not in seen:
            seen.add(ac)
            out.append(ac)
    return out


def build_athena_query(
    metric=None,
    depth=None,
    start_date=None,
    end_date=None,
    columns: Optional[Sequence[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    limit: Optional[int] = None,
    order_by: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build a single SELECT statement for Athena. ``metric`` is accepted for API
    compatibility but does not affect SQL (no stable column mapping for a free-form label).
    ``depth`` adds ``depthm = <number>`` when set. ``startDate`` / ``endDate`` add date
    predicates on column ``date`` when that column is allowlisted.
    """
    _ = metric
    table = _assert_table_name(os.environ.get("ATHENA_TABLE", "bottle_table"))
    lim = _parse_limit(limit)
    col_list = _normalize_columns(columns)
    norm_filters = _normalize_filters(filters)
    ob = _normalize_order_by(order_by)

    where_parts: List[str] = []
    for i, f in enumerate(norm_filters):
        try:
            where_parts.append(_one_predicate(f["column"], f["op"], f["value"]))
        except ValueError as e:
            raise ValueError(f"filters[{i}]: {e}") from e

    if depth is not None and depth != "":
        try:
            d = _coerce_number(depth)
        except ValueError as e:
            raise ValueError(f"depth: {e}") from e
        where_parts.append(f"{_assert_column('depthm')} = {_format_scalar(d)}")

    if start_date not in (None, "") or end_date not in (None, ""):
        if "date" not in ALLOWED_COLUMNS:
            pass
        else:

            def _as_date_str(v: Any, label: str) -> Optional[str]:
                if v is None or v == "":
                    return None
                if not isinstance(v, str):
                    raise ValueError(f"{label} must be a YYYY-MM-DD string")
                t = v.strip()
                return t or None

            sd = _as_date_str(start_date, "startDate")
            ed = _as_date_str(end_date, "endDate")
            if sd and ed:
                _assert_iso_date(sd, "startDate")
                _assert_iso_date(ed, "endDate")
                where_parts.append(_one_predicate("date", "BETWEEN", [sd, ed]))
            elif sd:
                _assert_iso_date(sd, "startDate")
                where_parts.append(_one_predicate("date", ">=", sd))
            elif ed:
                _assert_iso_date(ed, "endDate")
                where_parts.append(_one_predicate("date", "<=", ed))

    select_list = "*"
    if col_list is not None:
        select_list = ", ".join(col_list)

    sql = f"SELECT {select_list} FROM {table}"
    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)
    if ob is not None:
        sql += f" ORDER BY {_assert_column(ob['column'])} {ob['direction']}"
    sql += f" LIMIT {lim}"
    return sql
