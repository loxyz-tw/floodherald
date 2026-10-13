# Taiwan local water-safety lists: team compilation

This folder holds a team research compilation of water-safety lists published by Taiwan's local jurisdictions, including third-party reposts with unconfirmed original publishers. The lists include dangerous-water inventories, recreation restrictions, disaster-response restrictions, and drowning incident or rescue records.

It is **not** an official national list, a count of unique sites, or a count of flood-risk locations. In this document, 780 and 363 are **entries** (rows produced by the rules below), and N1 and N2 are **name groups** of rivers and streams. Neither entries nor name groups are verified counts of unique rivers or sites.

Accessed: 14 October 2026. The entry point was the Sports Administration's iPlay portal page *危險水域各縣市公告資訊* (<https://iplay.sports.gov.tw/Dangerouswater>), which links each jurisdiction's source. Where an iPlay link held no usable list, we used another published source from the same jurisdiction. `sources.csv` lists the sources actually used.

## Files

| File | Content |
|---|---|
| `entries.csv` | One row per entry (780 rows). Includes the source ID, the position in the original list (`source_row`), the location text as written in the source, our water-type classification and its basis, the source's content nature and status, the data date, and the URL. `entry_id` is our own sequence number, not an original row number. |
| `sources.csv` | One row per source (21 rows: 20 list sources plus 1 supporting reference), with license or terms where confirmed. |
| `rivers_dedup.csv` | River/stream entries grouped into name groups. Each row is an N1 unit (`n1_unit`) with its nationwide N2 group (`national_group_id`, `national_group_name`) and member entry IDs. Excluded entries are listed with the reason. |

## Summary

| Measure | Value |
|---|---:|
| Jurisdictions with a usable list | 21 of 22 (no list found for Chiayi City) |
| Entries, all types | 780 |
| Entries classified as river/stream | 363 (291 explicit in source, 72 inferred) |
| **N1**: river/stream name groups within each jurisdiction | **128** |
| **N2**: river/stream name groups nationwide | **115** |

Water-type breakdown of all 780 entries: river/stream 363, coast/sea 185, lake/reservoir/pond 108, other 72, unknown 52.

N1 and N2 group river/stream **names** that appear in these lists. They are not verified counts of unique rivers or sites, not counts of flood-risk or installation sites, and not lower bounds on any of these.

## Method

1. **One entry = one location row as listed in the source.** Rivers split into segments in the source stay as separate entries. Apparent duplicates within a source are kept, with one exception: in the Miaoli list, identical locations repeat because they have different managing agencies, so those repeats were collapsed (44 rows became 37 entries). The Yunlin disaster-response list has two hillside landslide areas that are not water bodies; they were excluded (32 rows became 30 entries). Pingtung publishes one file per year; only the latest year (2023 data) was used.
2. **Water type** (`water_type`) is our classification from the wording of the location text:
   - `river_stream`: 溪, 河, 川, 流域, river mouth, waterfall
   - `coast_sea`: sea area, beach, coast, fishing harbour, berth, pier, breakwater, lagoon, snorkelling area
   - `lake_reservoir_pond`: lake, 潭, reservoir, 埤, pond
   - `other`: irrigation canal, drain, wetland, fish/shrimp pond, swimming pool, well, intake, settling basin
   - `unknown`: only a road, address, temple, landmark, or unlabeled map marker
3. **Classification basis** (`classification_basis`):
   - `explicit_in_source`: the source names a water body or water-body type
   - `inferred`: we classified the entry from a bridge name, levee, waterfall or local knowledge. For example, entries that give only "under X bridge" are classified as river/stream.
   - `external_source(S21)`: one entry reclassified as coast/sea from a separate official notice
   - `not_classified`: the entry has no classification
4. **Content nature** (`content_nature`, per source):
   - `hazard_inventory`: dangerous-water or drowning-prevention list
   - `recreation_restriction`: prohibition or restriction under tourism law (one source includes a conservation zone)
   - `disaster_response_restriction`: areas closed during disaster response
   - `incident_records` / `rescue_records`: places where drowning incidents or rescues occurred
   - `hazard_or_incident_unclear`: the title refers to past incidents, but the content reads as a whole-river inventory
5. **Source status** (`source_status`):
   - `agency_original`: published by the agency
   - `official_compilation`: an official body compiling or relaying other agencies' data
   - `repost_origin_unconfirmed`: reposted by a third party; the original publisher was not confirmed
   - `origin_unconfirmed`: the publisher is not stated
6. **Data date** is the date shown in or on the source: its publication, update or document date. Several sources state a data year different from the platform update date; see `sources.csv`.

## River/stream name groups (N1, N2)

We start from the 363 river/stream entries. The unit is *jurisdiction + named water body*.

- **Grouping.** Every entry naming the same river or stream joins one group, however many segments, bridges or incidents it lists.
- **Name variants unified:**
  - 卑南大溪 = 卑南溪, 濁水流域 = 濁水溪, 東埔蚋 = 東埔蚋溪
  - Love River water, tributary and basin entries form one Love River (愛河) group.
  - 北/南太麻里溪出海口 form one Taimali River group, and 南澳南（北）溪 forms one group.
  - One Taichung entry names two rivers, so it joins two groups.
- **Known aliases or upstream names of the same river are merged:**
  - Kaohsiung 鳳山溪 and 前鎮河 form one group. The Kaohsiung City Government describes the lower Fengshan River as Qianzhen River (<https://takao.kcg.gov.tw/article/1820>). The city's Environmental Protection Bureau lists 鳳山溪（含前鎮河） (<https://ksepb.kcg.gov.tw/Folder/examine02>).
  - Nantou 平林溪 is merged into 貓羅溪. The Water Resources Agency's planning report is titled as covering 貓羅溪本流、上游平林溪、支流樟平溪 (<https://web.wra.gov.tw/WraLib/wSite/books_75964>). 樟平溪 is a tributary and stays a separate group.
  - Other aliases have not been checked.
- **Entries without a river name never join or create a group.** These are entries giving only a bridge, levee, landmark, waterfall, unnamed river mouth or riverside park. All 100 such entries are excluded and listed in `rivers_dedup.csv` with the reason. External checks confirmed that two excluded entries are not on the Beinan River main stem:
  - E572 (old Luming Bridge) is on the Luye River (鹿野溪): Executive Yuan Gazette, Beinan River system river-area notice, <https://gazette.nat.gov.tw/EG_FileManager/eguploadpub/eg026158/ch04/type3/gov31/num9/Eg.htm>.
  - E574 (Danan Bridge, Dongxing Village) is on the Danan River (大南溪): Forestry and Nature Conservation Agency, <https://www.forest.gov.tw/0000014/0067113>.
  - The 100 exclusions include five landmark-named mountain gullies in Yunlin, which may coincide with other listed streams.
- **N1 = 128.** Groups are counted separately in each jurisdiction, so a river crossing jurisdictions counts once in each.
- **N2 = 115.** N1 groups are merged by name nationwide after removing the suffixes 「（支流）」 and 「（流域）」. Yunlin's 清水溪（支流） therefore joins 清水溪 in Nantou and Chiayi County. `national_group_id` gives the exact N1→N2 mapping. Different rivers that share a name are also merged, for example 北勢溪 in New Taipei and in Nantou, and 南勢溪 in New Taipei and in Miaoli.

The name groups reflect the stated rules only. Some excluded entries lie on rivers not otherwise named. Unidentified aliases, upstream/downstream renamings and tributary relationships may remain. So N1 and N2 can be either above or below the true number of distinct rivers.

## Limitations

- **Mixed years and definitions.** Source dates run from 2011 to 2026. Some lists are inventories, some are legal restrictions, one is a disaster-response closure list, and six are incident or rescue records (Taoyuan, Miaoli, Kaohsiung, Pingtung, Hualien, Kinmen). Entries are not comparable across jurisdictions and are not current official totals.
- **Overlap and gaps.** Entries mix whole rivers, segments, bridges, street addresses, sea areas and unnamed map markers. Spatial overlap was not resolved, so the 780 entries are neither a count of unique sites nor a lower bound on one. Chiayi City has no list in this compilation; that does not mean it has zero locations. The Lienchiang (Matsu) source is a map with three unnamed markers.
- **Unconfirmed origins.** The Chiayi County list (2011) is a school-website repost, and the Taitung list (2013) is a relay on a public Facebook page. In both, the original publisher is inferred only from the fire-brigade units named in the tables. The Tainan PDF does not state its publisher. The Taitung album may require a Facebook account to view, which limits reproducibility.
- **Classifications include inference.** Water types are team classifications. River/stream does not mean the site is suitable for flash-flood warning equipment.
- **Text as in source.** Location text is copied as published, including apparent typos or unreadable characters in the original files (for example `?地段`, `仙?橋`, `?凰瀑布`, `中埔相`, `坑內僑`). These are marked here as "as in source, unverified" and were not corrected.
- **Addresses.** Some entries contain street addresses published in incident records. They locate the water body only and say nothing about residents or property owners.

## Licensing

- **Team-authored material.** This README, the classification fields (`water_type`, `classification_basis`, `content_nature`, `source_status`), the name-group mappings, and the arrangement of the CSV files are the team's work. They are released under the same terms as the repository that hosts them.
- **Third-party material.** The location text, dates and other facts come from the sources in `sources.csv`. The repository license does not relicense those sources. `sources.csv` records each source's `license_or_terms`:
  - Where a source is published under the Open Government Data License v1.0 (政府資料開放授權條款-第1版), reuse must follow that license, including its attribution requirement (`attribution_note`).
  - Where the terms are `unconfirmed`, we have not verified reuse terms; consult the source.
  - Original documents, images and tables (PDFs, Facebook album images, web pages) are not redistributed here.
