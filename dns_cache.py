import redis
import dns.resolver
import time
import json 

# --- Configuration ---
# This is now the default TTL for *negative caching* only
NEGATIVE_CACHE_TTL_SECONDS = 60

# --- Redis Connection ---
try:
    r = redis.Redis(
        host='localhost', 
        port=6379, 
        db=0,
        decode_responses=True
    )
    r.ping()
    print("Connected to Redis successfully!")
except redis.exceptions.ConnectionError as e:
    print(f"Could not connect to Redis: {e}")
    r = None

# --- Core DNS Function  ---

def get_dns_lookup(domain: str, record_type: str = 'A'):
    """
    Performs a DNS lookup for a specific record type using a Redis cache.
    
    Caches successes in a Hash (Key: dns:cache:<domain>:<type>)
    Caches failures in a String (Key: dns:nx:<domain>:<type>)
    """
    if r is None:
        return {"error": "Redis connection failed"}, 0, "error", 0.0
        
    # NEW: Type-specific keys
    cache_key = f"dns:cache:{domain}:{record_type}"
    negative_key = f"dns:nx:{domain}:{record_type}"
    
    start_time = time.perf_counter()
    
    # 1. Check for negative cache (String)
    if r.get(negative_key):
        ttl = r.ttl(negative_key)
        duration_ms = (time.perf_counter() - start_time) * 1000
        return {"error": f"{record_type} record not found (Cached)"}, ttl, "hit (negative)", duration_ms
        
    # 2. Check for successful cache (Hash)
    cached_response = r.hgetall(cache_key)
    
    if cached_response:
        # --- Cache Hit ---
        ttl = r.ttl(cache_key)
        records = json.loads(cached_response.get("records", "[]"))
        duration_ms = (time.perf_counter() - start_time) * 1000
        return records, ttl, "hit", duration_ms

    # --- 3. Cache Miss ---
    print(f"Cache MISSED for {domain} ({record_type}). Performing real lookup...")
    
    try:
        resolver = dns.resolver.Resolver()
        # Use the provided record_type
        answers = resolver.resolve(domain, record_type)
        
        # --- Got a successful answer ---
        
        record_ttl = answers.rrset.ttl
        
        # Get ALL records, converting them to simple strings
        # This handles A, MX, TXT, NS, etc. cleanly
        records_list = []
        for a in answers:
            if record_type == 'MX':
                records_list.append(f"{a.preference} {a.exchange}")
            elif record_type == 'TXT':
                # TXT records are bytes, decode them and clean up quotes
                records_list.append(b''.join(a.strings).decode('utf-8'))
            else:
                records_list.append(str(a))
        
        records_json = json.dumps(records_list)
        
        payload = {
            "records": records_json,
            "fetched_at": time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
            "record_type": record_type
        }
        
        pipe = r.pipeline()
        pipe.hset(cache_key, mapping=payload)
        pipe.expire(cache_key, record_ttl)
        pipe.execute()
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        return records_list, record_ttl, "miss", duration_ms

    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        # --- Got a "Not Found" or "No Answer" error ---
        r.setex(negative_key, NEGATIVE_CACHE_TTL_SECONDS, "NXDOMAIN")
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        error_msg = f"{record_type} record not found for {domain}"
        return {"error": error_msg}, NEGATIVE_CACHE_TTL_SECONDS, "miss (negative)", duration_ms
        
    except Exception as e:
        print(f"Error during DNS lookup: {e}")
        return {"error": str(e)}, 0, "error", 0.0