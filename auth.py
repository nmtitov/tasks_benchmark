import random
import string

import aiohttp

# Per-request timeout guard (aiohttp default is 5 min — a stalled connection
# would otherwise hang setup/cleanup indefinitely under server saturation).
_TIMEOUT = aiohttp.ClientTimeout(total=20)


def _random_suffix(length=8):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


class BenchUser:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.email = f"bench_{_random_suffix()}@test.local"
        self.password = f"bench_pass_{_random_suffix(16)}"
        self.token = None
        self.user_id = None

    async def signup(self, session):
        url = f"{self.base_url}/api/auth/signup"
        payload = {"email": self.email, "password": self.password}
        async with session.post(url, json=payload) as resp:
            if resp.status != 201:
                text = await resp.text()
                raise RuntimeError(f"Signup failed ({resp.status}): {text}")
            data = await resp.json()
            self.token = data["token"]

    async def signin(self, session):
        url = f"{self.base_url}/api/auth/signin"
        payload = {"email": self.email, "password": self.password}
        async with session.post(url, json=payload) as resp:
            if resp.status != 201:
                text = await resp.text()
                raise RuntimeError(f"Signin failed ({resp.status}): {text}")
            data = await resp.json()
            self.token = data["token"]

    async def get_user_id(self, session):
        url = f"{self.base_url}/api/auth/validate-token"
        headers = {"X-Token": self.token}
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Validate-token failed ({resp.status}): {text}")
            self.user_id = await resp.text()
        return self.user_id

    async def delete(self, session):
        url = f"{self.base_url}/api/user/delete"
        headers = {"X-Token": self.token}
        async with session.delete(url, headers=headers) as resp:
            if resp.status not in (204, 200):
                text = await resp.text()
                raise RuntimeError(f"Delete user failed ({resp.status}): {text}")

    def auth_headers(self):
        return {"X-Token": self.token}


async def create_bench_user(base_url):
    async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
        user = BenchUser(base_url)
        await user.signup(session)
        await user.get_user_id(session)
        print(f"  Created bench user: {user.email} (id: {user.user_id})")
        return user


async def cleanup_bench_user(user):
    async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
        await user.delete(session)
        print(f"  Deleted bench user: {user.email}")
