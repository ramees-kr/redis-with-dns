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

def get_dns_lookup(domain: str):
    """
    Performs a DNS 'A' record lookup using a more advanced Redis cache.
    
    1. Checks for a "negative cache" (String) for NXDOMAIN.
    2. Checks for a "cache" (Hash) for successful lookups.
    3. On miss, performs a real DNS lookup.
       - Caches successes in a Hash with the record's real TTL.
       - Caches failures (NXDOMAIN) in a String with a fixed TTL.
    """
    if r is None:
        return {"error": "Redis connection failed"}, 0, "error", 0.0
        
    cache_key = f"dns:cache:{domain}"
    negative_key = f"dns:nx:{domain}"
    
    start_time = time.perf_counter()
    
    # 1. Check for negative cache (String)
    if r.get(negative_key):
        ttl = r.ttl(negative_key)
        duration_ms = (time.perf_counter() - start_time) * 1000
        return {"error": "Domain not found (Cached)"}, ttl, "hit (negative)", duration_ms
        
    # 2. Check for successful cache (Hash)
    # HGETALL is O(N) where N is fields, which is small.
    cached_response = r.hgetall(cache_key)
    
    if cached_response:
        # --- Cache Hit ---
        ttl = r.ttl(cache_key)
        # Parse the JSON string back into a list
        records = json.loads(cached_response.get("A_records", "[]"))
        duration_ms = (time.perf_counter() - start_time) * 1000
        return records, ttl, "hit", duration_ms

    # --- 3. Cache Miss ---
    print(f"Cache MISSED for {domain}. Performing real lookup...")
    
    try:
        resolver = dns.resolver.Resolver()
        # By default, resolve() follows CNAMEs for us
        answers = resolver.resolve(domain, 'A')
        
        # --- Got a successful answer ---
        
        # Get the REAL TTL from the response
        record_ttl = answers.rrset.ttl
        
        # Get ALL 'A' records, not just the first one
        ip_addresses = [str(a) for a in answers]
        
        # Store as a JSON string
        ip_json = json.dumps(ip_addresses)
        
        # Prepare the Hash payload
        payload = {
            "A_records": ip_json,
            "fetched_at": time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
            "record_type": "A"
        }
        
        # Use a pipeline for an atomic transaction
        pipe = r.pipeline()
        # Create the hash with all its fields
        pipe.hset(cache_key, mapping=payload)
        # Set the dynamic TTL on the *entire key*
        pipe.expire(cache_key, record_ttl)
        pipe.execute()
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        return ip_addresses, record_ttl, "miss", duration_ms

    except dns.resolver.NXDOMAIN:
        # --- Got a "Domain Not Found" error ---
        
        # Use SETEX to set the negative cache (our String demo)
        r.setex(negative_key, NEGATIVE_CACHE_TTL_SECONDS, "NXDOMAIN")
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        return {"error": "Domain not found"}, NEGATIVE_CACHE_TTL_SECONDS, "miss (negative)", duration_ms
        
    except Exception as e:
        print(f"Error during DNS lookup: {e}")
        return {"error": str(e)}, 0, "error", 0.0