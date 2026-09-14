---
name: db-designer
description: >
  Database design skill. Use when designing new tables, adding ERD files
  (.erd.json), or writing DDL. Load this skill before producing any database
  design artifacts.
---

# Database Design Skill

You are now equipped to produce database design artifacts. Load this skill
into the current conversation — no separate subagent needed.

## ERD File Format (.erd.json)

Output to the project's database design directory (follow the convention of
existing ERD files in this project, e.g. `doc/2-database-design/增量/{序号}-{主题}.erd.json`).

```json
{
  "$schema": "https://raw.githubusercontent.com/dineug/erd-editor/main/json-schema/schema.json",
  "version": "3.0.0",
  "settings": {
    "width": 2000, "height": 2000,
    "canvasType": "ERD", "language": 128,
    "tableNameCase": 4, "columnNameCase": 2
  },
  "doc": { "tableIds": [...], "relationshipIds": [...], "indexIds": [...] },
  "collections": {
    "tableEntities": {
      "nanoid1": {
        "id": "nanoid1",
        "name": "table_name",
        "comment": "表注释",
        "columnIds": [...],
        "seqColumnIds": [...],
        "ui": { "x": 56, "y": 461, "zIndex": 1, "widthName": 169, "widthComment": 74 }
      }
    },
    "tableColumnEntities": {
      "nanoid2": {
        "id": "nanoid2",
        "tableId": "nanoid1",
        "name": "column_name",
        "comment": "列注释",
        "dataType": "BIGINT",
        "default": "",
        "options": 10,
        "ui": { "keys": 1, "widthName": 60, "widthComment": 60, "widthDataType": 60, "widthDefault": 60 }
      }
    }
  }
}
```

- Generate stable nanoid-like IDs for each table/column/relationship
- `options`: 10 = PK, 8 = NOT NULL
- `ui.keys`: 1 = key icon shown, 0 = no icon
- Workspace: ERD file encoding must be UTF-8 with BOM

## DDL Convention

```sql
CREATE TABLE `table_name` (
  `id` BIGINT NOT NULL COMMENT '主键',
  `column` VARCHAR(128) DEFAULT '' COMMENT '列注释',
  PRIMARY KEY (`id`),
  KEY `idx_xxx` (`column`) COMMENT '索引注释'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='表注释';
```

- Engine InnoDB, charset utf8mb4
- Every column must have COMMENT
- Index naming: PRIMARY KEY, UNIQUE KEY `uk_xxx`, KEY `idx_xxx`

## Data Dictionary Markdown (.md)

Every `.erd.json` gets a read-only companion data dictionary Markdown so field
definitions are reviewable without opening the editor:

- Tool: `tools/erd2md.py` (ships with this skill, works on any ERD Editor v3 `.erd.json`)
- Output: same directory, same base name → `NN-<主题>.md`
- Content: meta/stats, legend, domain overview (parsed from canvas memos), per-table
  column table (name · type · key flags · default · comment, FK annotated as
  `父表.列`), per-table index list, appendix of full relationship list.
- Regenerate after any `.erd.json` change:
  `python <skill>/tools/erd2md.py <path>.erd.json`

```text
NN-<主题>.erd.json  --ERD Editor 源（可编辑/评审）
        └─(erd2md)--> NN-<主题>.md   （只读数据字典，勿手改）
```

## Workflow

1. Read the design document's database change section
2. Read existing ERD files in the project's database design directory for format reference
3. Produce: ERD file → DDL + data dictionary `.md` (same base name)
4. Report produced files
