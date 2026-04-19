/** Keep in sync with backend/hello_world/query_builder.py ALLOWED_COLUMNS and data/schemas/calcofi_schema.sql bottle_table */
export const ATHENA_ALLOWED_COLUMNS = [
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
] as const;

export type AthenaAllowlistedColumn = (typeof ATHENA_ALLOWED_COLUMNS)[number];

export const ATHENA_ALLOWED_OPS = ["=", "!=", "<", "<=", ">", ">=", "BETWEEN"] as const;

export type AthenaFilterOp = (typeof ATHENA_ALLOWED_OPS)[number];
