# Source Data Notes (2026-03-04)

## Prepared file
- `bot/data/test.json` is implementation-ready and aligned with materials in `source/`.

## Normalization decisions
- Test uses 8 questions in single pass.
- Each question requires 2 answers:
  - first pick from 6 options
  - second pick from remaining 5 options (first pick removed)
- Type codes are fixed as `A..F`:
  - `A` Педант
  - `B` Эстет
  - `C` Креативщик
  - `D` Приятель
  - `E` Артист
  - `F` Невидимка
- Scoring uses +1 for selected option type and deterministic tie handling by type order `A..F`.
- Secondary result is a single type code: max among codes excluding leading type.

## Ambiguity handled
- In source question 7, option labels (`A..F`) describe abilities, not direct type codes.
- `test.json` maps by semantics:
  - "харизму" -> `E`
  - "структуре" -> `A`
  - "дисциплину/рамки" -> `A`
  - "монтажу" -> `B`
  - "привыкнуть к съёмке" -> `E`
  - "оставаться за кадром" -> `F`

## Media contract for implementation
- `test.json` references `type_a.png ... type_f.png`.
- Place renamed/exported final images into `bot/media/` with those filenames.
