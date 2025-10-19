import redis
import dns.resolver

# --- Configuration ---
# This is our cache TTL (Time To Live) in seconds.
# We'll cache DNS records for 60 seconds.
CACHE_TTL_SECONDS = 60

# --- Redis Connection ---
# We create one connection pool that our functions can reuse.
# It assumes Redis is running on localhost:6379
try:
    r = redis.Redis(
        host='localhost', 
        port=6379, 
        db=0,
        decode_responses=True # Automatically decodes responses from bytes to strings
    )
    r.ping()
    print("Connected to Redis successfully!")
except redis.exceptions.ConnectionError as e:
    print(f"Could not connect to Redis: {e}")
    r = None

# --- Core DNS Function ---

def get_dns_lookup(domain: str):
    """
    Performs a DNS 'A' record lookup using a Redis cache.
    
    1. Checks Redis for a cached IP.
    2. If hit, returns the IP, TTL, and 'hit' status.
    3. If miss, performs a real DNS lookup.
    4. Caches the result in Redis with a TTL.
    5. Returns the IP, TTL, and 'miss' status.
    """
    if r is None:
        return None, 0, "Redis connection failed"
        
    cache_key = f"dns:{domain}"
    
    try:
        # 1. Check Redis for a cached IP
        cached_ip = r.get(cache_key)
        
        if cached_ip:
            # 2. Cache Hit
            ttl = r.ttl(cache_key)
            return cached_ip, ttl, "hit"

        # 3. Cache Miss - perform the real lookup
        print(f"Cache MISSED for {domain}. Performing real lookup...")
        
        # Use dnspython to find the 'A' record
        resolver = dns.resolver.Resolver()
        answers = resolver.resolve(domain, 'A')
        
        # Get the first IP address from the answer
        ip_address = str(answers[0])
        
        # 4. Cache the result in Redis
        # Use SETEX to set the key with an automatic expiration
        r.setex(cache_key, CACHE_TTL_SECONDS, ip_address)
        
        # 5. Return the new data
        return ip_address, CACHE_TTL_SECONDS, "miss"

    except dns.resolver.NXDOMAIN:
        # The domain does not exist
        return "Domain not found", 0, "miss"
    except Exception as e:
        # Other DNS or general errors
        print(f"Error during DNS lookup: {e}")
        return None, 0, f"error: {e}"