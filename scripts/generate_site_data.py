#!/usr/bin/env python3
"""Generate website metadata from readme.docx and swc.zip."""

from __future__ import annotations

import json
import re
import shutil
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
DATA_DIR = PUBLIC / "data"
THUMB_DIR = PUBLIC / "assets" / "thumbnails"
README = ROOT / "readme.docx"
SWC_ZIP = ROOT / "swc.zip"

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

FOLDER_ALIASES = {
    "power-grid": "power-grid-entergy",
}

DISPLAY_NAMES = {
    "arabidopsis": "Arabidopsis",
    "tropical-tree": "Tropical Tree",
    "coral": "Coral",
    "vascular": "Vascular",
    "neuron-fruit-fly-hemibrain": "Fruit Fly Hemibrain Neurons",
    "neuron-human-h01": "Human H01 Neurons",
    "power-grid": "Power Grid",
    "fungal": "Fungal Networks",
    "watercourse-france": "Watercourse France",
    "integrated-circuit-pharosc": "Integrated Circuit Pharosc",
}

DATASET_TAGS = {
    "arabidopsis": ["plant", "growth", "point cloud"],
    "tropical-tree": ["forest", "lidar", "tree"],
    "coral": ["marine", "mesh", "branching"],
    "vascular": ["human", "pulmonary", "vasculature"],
    "neuron-fruit-fly-hemibrain": ["neuron", "brain", "connectomics"],
    "neuron-human-h01": ["neuron", "brain", "connectomics"],
    "power-grid": ["infrastructure", "pixel image", "graph"],
    "fungal": ["mycelium", "skeleton", "growth"],
    "watercourse-france": ["geospatial", "river", "hydrology"],
    "integrated-circuit-pharosc": ["chip", "voxel image", "layout"],
}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def cell_text(cell: ET.Element) -> str:
    return "".join(t.text or "" for t in cell.findall(".//w:t", NS)).strip()


def read_docx_tables() -> list[list[list[str]]]:
    with ZipFile(README) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))

    tables: list[list[list[str]]] = []
    for table in root.findall(".//w:tbl", NS):
        rows: list[list[str]] = []
        for tr in table.findall("w:tr", NS):
            rows.append([cell_text(tc) for tc in tr.findall("w:tc", NS)])
        tables.append(rows)
    return tables


def read_docx_source_urls() -> list[str]:
    with ZipFile(README) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))
        rel_root = ET.fromstring(zf.read("word/_rels/document.xml.rels"))

    relationships = {
        rel.attrib["Id"]: rel.attrib.get("Target", "")
        for rel in rel_root.findall("rel:Relationship", NS)
    }
    tables = root.findall(".//w:tbl", NS)
    if len(tables) < 2:
        return []

    urls: list[str] = []
    for tr in tables[1].findall("w:tr", NS)[1:]:
        cells = tr.findall("w:tc", NS)
        if len(cells) < 3:
            urls.append("")
            continue
        hyperlink = cells[2].find(".//w:hyperlink", NS)
        relationship_id = hyperlink.attrib.get(f"{{{NS['r']}}}id") if hyperlink is not None else ""
        urls.append(relationships.get(relationship_id, cell_text(cells[2])))
    return urls


def extract_thumbnails() -> list[str]:
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    for existing in THUMB_DIR.glob("*.png"):
        existing.unlink()

    image_paths: list[str] = []
    with ZipFile(README) as zf:
        media = sorted(
            [p for p in zf.namelist() if p.startswith("word/media/image")],
            key=lambda p: int(re.search(r"image(\d+)", p).group(1)),
        )
        for index, member in enumerate(media, start=1):
            target = THUMB_DIR / f"dataset-{index:02d}.png"
            with zf.open(member) as source, target.open("wb") as dest:
                shutil.copyfileobj(source, dest)
            image_paths.append(f"assets/thumbnails/{target.name}")
    return image_paths


def read_zip_manifest() -> dict:
    groups: dict[str, dict] = defaultdict(
        lambda: {"fileCount": 0, "totalBytes": 0, "representativeFiles": []}
    )
    total_files = 0
    total_bytes = 0

    with ZipFile(SWC_ZIP) as zf:
        for info in zf.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".swc"):
                continue
            folder = info.filename.split("/", 1)[0]
            group = groups[folder]
            group["fileCount"] += 1
            group["totalBytes"] += info.file_size
            if len(group["representativeFiles"]) < 6:
                group["representativeFiles"].append(info.filename)
            total_files += 1
            total_bytes += info.file_size

    folders = {
        name: {
            **values,
            "totalMB": round(values["totalBytes"] / 1024 / 1024, 2),
        }
        for name, values in sorted(groups.items())
    }
    return {
        "archive": "swc.zip",
        "archiveBytes": SWC_ZIP.stat().st_size,
        "archiveMB": round(SWC_ZIP.stat().st_size / 1024 / 1024, 2),
        "uncompressedBytes": total_bytes,
        "uncompressedGB": round(total_bytes / 1024 / 1024 / 1024, 2),
        "swcFileCount": total_files,
        "folders": folders,
    }


def boolean_format(value: str):
    normalized = value.strip().lower()
    if normalized == "y":
        return True
    if normalized == "n":
        return False
    if normalized in {"n/a", "na"}:
        return "na"
    return value


def build_datasets(
    tables: list[list[list[str]]], source_urls: list[str], thumbnails: list[str], manifest: dict
) -> list[dict]:
    availability_rows = tables[0][1:]
    description_rows = tables[1][1:]
    descriptions = {
        slugify(availability_row[1]): {
            "description": description_row[1],
            "sourceUrl": source_urls[index]
            if index < len(source_urls)
            else description_row[2],
        }
        for index, (availability_row, description_row) in enumerate(
            zip(availability_rows, description_rows)
        )
        if len(availability_row) >= 2 and len(description_row) >= 3
    }

    datasets = []
    for index, row in enumerate(availability_rows):
        if len(row) < 8:
            continue
        slug = slugify(row[1])
        archive_folder = FOLDER_ALIASES.get(slug, slug)
        folder_stats = manifest["folders"].get(archive_folder, {})
        desc = descriptions.get(slug, {})
        sample_text = row[2].replace("(", " (")

        datasets.append(
            {
                "slug": slug,
                "name": DISPLAY_NAMES.get(slug, row[1]),
                "shortName": row[1],
                "sampleCount": sample_text,
                "swcFileCount": folder_stats.get("fileCount"),
                "originalDataType": row[3],
                "formats": {
                    "skeletonSwc": boolean_format(row[4]),
                    "mesh": boolean_format(row[5]),
                    "pixelVoxelImage": boolean_format(row[6]),
                    "treeGraph": boolean_format(row[7]),
                },
                "description": desc.get("description", ""),
                "sourceLinks": [
                    {"label": "Original source", "url": desc.get("sourceUrl", "")}
                ],
                "zenodo": {
                    "recordUrl": "https://zenodo.org/records/17154400",
                    "doi": "",
                    "version": "",
                },
                "assets": {
                    "thumbnail": thumbnails[index] if index < len(thumbnails) else "",
                    "preview": "",
                },
                "archive": {
                    "zip": "swc.zip",
                    "folder": archive_folder,
                    "uncompressedMB": folder_stats.get("totalMB"),
                    "representativeFiles": folder_stats.get("representativeFiles", []),
                },
                "tags": DATASET_TAGS.get(slug, []),
            }
        )
    return datasets


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tables = read_docx_tables()
    source_urls = read_docx_source_urls()
    thumbnails = extract_thumbnails()
    manifest = read_zip_manifest()
    datasets = build_datasets(tables, source_urls, thumbnails, manifest)

    site_meta = {
        "title": "Physical Network Dataset",
        "domain": "physical.network",
        "description": "A data registry for physical network skeletons, meshes, images, and graph representations.",
        "updatedFrom": {
            "readme": "readme.docx",
            "archive": "swc.zip",
        },
        "release": {
            "label": "Current local release",
            "zenodoRecordUrl": "https://zenodo.org/records/17154400",
            "doi": "",
            "date": "",
        },
        "stats": {
            "collections": len(datasets),
            "swcFiles": manifest["swcFileCount"],
            "archiveMB": manifest["archiveMB"],
            "uncompressedGB": manifest["uncompressedGB"],
        },
    }

    (DATA_DIR / "datasets.json").write_text(
        json.dumps({"meta": site_meta, "datasets": datasets}, indent=2) + "\n",
        encoding="utf-8",
    )
    (DATA_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(datasets)} datasets and {manifest['swcFileCount']} SWC file records.")


if __name__ == "__main__":
    main()
