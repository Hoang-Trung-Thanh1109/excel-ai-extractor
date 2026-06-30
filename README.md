# Excel AI Extractor

Ung dung desktop de tao file Excel tu:

- Prompt thuong

Ung dung dung Gemini 2.5 Flash va luu ket qua thanh workbook Excel da format san.

## Chay app

1. Cai dat dependencies:

```bash
pip install -r requirements.txt
```

2. Chay:

```bash
python app.py
```

## Cach dung

- Mo `ui.py` va thay gia tri `GEMINI_API_KEY` bang API key that.
- Viet prompt mo ta bang du lieu ban muon tao.
- Bam `Tao Excel`.

## Dau ra

File Excel se duoc tao voi:

- Header xanh
- Freeze pane
- Auto filter
- Zebra rows
- Auto width

Mặc dinh file duoc luu trong thu muc `outputs/`.

## Cau truc

- `app.py`: entry point
- `ui.py`: giao dien
- `ai_engine.py`: goi Gemini va tao JSON workbook spec
- `document_reader.py`: doc PDF/DOCX
- `excel_engine.py`: ghi va format Excel

## Ghi chu

- Khong dung `.env`
- Khong dung `venv`
- API key dang duoc cai truc tiep trong code de dung local nhanh, nhung khong nen chia se file nay neu co key that.
