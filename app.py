import asyncio, math, os, time
from typing import Any
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query

load_dotenv()
app = FastAPI(title="SearchTA", version="0.1.0")

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
RADIUS = float(os.getenv("SEARCH_RADIUS_M", "8000"))
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "10"))
QUERIES = ("canh cá rô", "canh cá rô đồng", "bún cá rô đồng")
URL = "https://places.googleapis.com/v1/places:searchText"
FIELDS = "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.googleMapsUri,places.currentOpeningHours"

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r=6371000.0
    p1,p2=math.radians(lat1),math.radians(lat2)
    dp=math.radians(lat2-lat1); dl=math.radians(lon2-lon1)
    a=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(math.sqrt(a))

async def one(client:httpx.AsyncClient,q:str,lat:float,lng:float)->list[dict[str,Any]]:
    body={"textQuery":q,"languageCode":"vi","regionCode":"VN",
          "locationBias":{"circle":{"center":{"latitude":lat,"longitude":lng},"radius":RADIUS}},
          "pageSize":20}
    headers={"X-Goog-Api-Key":API_KEY,"X-Goog-FieldMask":FIELDS,"Content-Type":"application/json"}
    r=await client.post(URL,json=body,headers=headers)
    r.raise_for_status()
    return r.json().get("places",[])

def score(p:dict[str,Any],lat:float,lng:float)->dict[str,Any]:
    loc=p.get("location") or {}
    d=haversine(lat,lng,float(loc.get("latitude",lat)),float(loc.get("longitude",lng)))
    rating=float(p.get("rating") or 0)
    votes=int(p.get("userRatingCount") or 0)
    # V1: rating dominates quality; log(votes) rewards confidence without letting huge chains dominate;
    # proximity gently penalizes far candidates.
    s=rating*2.0 + math.log10(votes+1)*0.9 - min(d/1000.0,20)*0.10
    return {"place_id":p.get("id"),"name":(p.get("displayName") or {}).get("text"),
            "rating":rating,"votes":votes,"distance_m":round(d),
            "open_now":(p.get("currentOpeningHours") or {}).get("openNow"),
            "address":p.get("formattedAddress"),"maps_url":p.get("googleMapsUri"),
            "score":round(s,4)}

@app.get("/health")
async def health(): return {"ok":True,"provider":"google-places-new"}

@app.get("/search")
async def search(lat:float=Query(...,ge=-90,le=90),lng:float=Query(...,ge=-180,le=180)):
    if not API_KEY: raise HTTPException(500,"GOOGLE_MAPS_API_KEY chưa được cấu hình")
    t0=time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=5.0,http2=True) as client:
            batches=await asyncio.gather(*(one(client,q,lat,lng) for q in QUERIES))
    except httpx.HTTPError as e:
        raise HTTPException(502,f"Google Places error: {e}")
    t1=time.perf_counter()
    unique={}
    for batch in batches:
        for p in batch:
            pid=p.get("id")
            if pid: unique[pid]=p
    ranked=sorted((score(p,lat,lng) for p in unique.values()),key=lambda x:x["score"],reverse=True)
    t2=time.perf_counter()
    return {"query_variants":QUERIES,"candidates":len(unique),"results":ranked[:MAX_RESULTS],
            "timing_ms":{"google":round((t1-t0)*1000),"rank":round((t2-t1)*1000),"total":round((t2-t0)*1000)}}
