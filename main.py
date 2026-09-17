"""
Pull NDW's "Planned Roadworks & Events" feed and look for PublicEvent
records that mention a given place (default: Eindhoven).

No API key needed - it's a plain public gzip XML file.
Run: python ndw_public_events.py
Optional: python ndw_public_events.py "Amsterdam"
"""

import gzip
import sys
import urllib.request
import xml.etree.ElementTree as ET

FEED_URL = "https://opendata.ndw.nu/planningsfeed_wegwerkzaamheden_en_evenementen.xml.gz"
NS = {
    "sit": "http://datex2.eu/schema/3/situation",
    "com": "http://datex2.eu/schema/3/common",
    "loc": "http://datex2.eu/schema/3/locationReferencing",
}
XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"


def text_or(default, element):
    """Grab the free-text value out of a DATEX II <values><value lang="nl">...</value></values> block."""
    if element is None:
        return default
    value = element.find(".//com:values/com:value", NS)
    return value.text if value is not None and value.text else default


def summarize_record(rec):
    record_id = rec.get("id", "unknown-id")

    source = text_or("unknown source", rec.find(".//sit:source", NS))

    start = rec.findtext(".//com:overallStartTime", default=None, namespaces=NS)
    end = rec.findtext(".//com:overallEndTime", default=None, namespaces=NS)

    delay_band = rec.findtext(".//sit:impact/sit:delays/sit:delayBand", default=None, namespaces=NS)
    cause_desc = text_or(None, rec.find(".//sit:cause/sit:causeDescription", NS))
    event_type = rec.findtext(".//sit:publicEventType", default=None, namespaces=NS)

    comments = []
    for c in rec.findall(".//sit:generalPublicComment", NS):
        value = text_or(None, c.find("sit:comment", NS))
        if value:
            comments.append(value)

    lat = rec.findtext(".//loc:pointCoordinates/loc:latitude", default=None, namespaces=NS)
    lon = rec.findtext(".//loc:pointCoordinates/loc:longitude", default=None, namespaces=NS)

    print(f"[{record_id}] reported by {source}")
    if start or end:
        print(f"  Active: {start or '?'}  ->  {end or '?'}")
    if event_type or cause_desc:
        print(f"  Type: {event_type or '?'} ({cause_desc or 'no description'})")
    if delay_band:
        print(f"  Expected delay: {delay_band}")
    if lat and lon:
        print(f"  Location: https://maps.google.com/?q={lat},{lon}")
    for comment in comments:
        print(f"  Note: {comment}")


def main():
    search_term = (sys.argv[1] if len(sys.argv) > 1 else "eindhoven").lower()

    print(f"Downloading {FEED_URL} ...")
    with urllib.request.urlopen(FEED_URL) as resp:
        compressed = resp.read()

    print("Decompressing and parsing XML (this file can be tens of MB, may take a moment)...")
    xml_bytes = gzip.decompress(compressed)
    root = ET.fromstring(xml_bytes)

    all_records = root.findall(".//sit:situationRecord", NS)
    public_events = [
        r for r in all_records
        if r.get(XSI_TYPE, "").endswith("PublicEvent")
    ]

    print(f"Total situationRecords in feed: {len(all_records)}")
    print(f"Of those, PublicEvent records: {len(public_events)}")

    matches = []
    for rec in public_events:
        blob = ET.tostring(rec, encoding="unicode").lower()
        if search_term in blob:
            matches.append(rec)

    print(f"PublicEvent records mentioning '{search_term}': {len(matches)}")
    if not matches:
        print("No matches - this just means none of the current PublicEvent")
        print("records have that place name in their text fields. The feed")
        print("mostly locates things via VILD location codes, not free text,")
        print("so this is a starting point, not a guarantee of absence.")
        return

    for i, rec in enumerate(matches, 1):
        print(f"\n--- Match {i} ---")
        summarize_record(rec)


if __name__ == "__main__":
    main()