import unittest
import asyncio
import os
import sys

# Set environment variable for test database BEFORE importing db module
os.environ["DATABASE_URL"] = "sqlite:///techstack_scout_test.db"

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import crawler.db as db


class TestDatabaseOperations(unittest.TestCase):
    """Unit tests for database schema and operations."""

    @classmethod
    def setUpClass(cls):
        """Set up test database and run migrations."""
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)
        cls.loop.run_until_complete(db.init_db())

    @classmethod
    def tearDownClass(cls):
        """Clean up and delete test database file."""
        cls.loop.run_until_complete(db.close_pool())
        cls.loop.close()
        
        # Clean up test database file
        if os.path.exists("techstack_scout_test.db"):
            try:
                os.remove("techstack_scout_test.db")
            except Exception as e:
                print(f"Warning cleaning up test db file: {e}")

    def test_1_add_and_get_domain(self):
        """Test adding a domain and retrieving it."""
        async def run():
            # Add new domain
            domain_id = await db.add_domain("example-test.com", "Test Industry", "US")
            self.assertIsNotNone(domain_id)
            self.assertGreater(domain_id, 0)
            
            # Retrieve domain by name
            domain = await db.get_domain_by_name("example-test.com")
            self.assertIsNotNone(domain)
            self.assertEqual(domain["domain"], "example-test.com")
            self.assertEqual(domain["industry"], "Test Industry")
            self.assertEqual(domain["country"], "US")
            self.assertEqual(domain["crawl_status"], "pending")
            
            # Retrieve domain by ID
            domain_by_id = await db.get_domain_by_id(domain_id)
            self.assertIsNotNone(domain_by_id)
            self.assertEqual(domain_by_id["domain"], "example-test.com")
            
        self.loop.run_until_complete(run())

    def test_2_duplicate_domain_handling(self):
        """Test handling duplicate domains (ON CONFLICT DO UPDATE)."""
        async def run():
            # Add duplicate domain with updated industry
            domain_id = await db.add_domain("example-test.com", "Updated Industry", "CA")
            
            # Retrieve to check updates
            domain = await db.get_domain_by_name("example-test.com")
            self.assertIsNotNone(domain)
            self.assertEqual(domain["id"], domain_id)
            self.assertEqual(domain["industry"], "Updated Industry")
            self.assertEqual(domain["country"], "CA")
            
        self.loop.run_until_complete(run())

    def test_3_add_detections(self):
        """Test registering technology detections and check leaderboard."""
        async def run():
            # Ensure domain exists
            domain_id = await db.add_domain("example-test.com")
            
            # Seed a test technology if needed (Google Analytics is in seed migration, let's fetch it)
            pool = await db.get_pool()
            async with pool.acquire() as conn:
                tech = await conn.fetchrow("SELECT slug FROM technologies LIMIT 1")
                self.assertIsNotNone(tech, "Technologies seed table is empty!")
                tech_slug = tech["slug"]
                
                # Add detection
                added = await db.add_tech_detection(
                    domain_id=domain_id,
                    tech_slug=tech_slug,
                    confidence=0.9,
                    method="script_src",
                    evidence="googletagmanager.com/gtm.js"
                )
                self.assertTrue(added)
                
                # Update domain status to 'crawled' (needed for view/leaderboard counts)
                await db.update_domain_crawl_result(
                    domain_id=domain_id,
                    status="crawled",
                    page_title="Example Title",
                    http_status=200,
                    page_size=1024
                )
                
                # Retrieve domain with detections
                domain = await db.get_domain_by_id(domain_id)
                self.assertIsNotNone(domain)
                self.assertGreater(len(domain["technologies"]), 0)
                self.assertEqual(domain["technologies"][0]["slug"], tech_slug)
                
                # Get leaderboard and verify counts
                leaderboard = await db.get_leaderboard()
                self.assertGreater(len(leaderboard), 0)
                
        self.loop.run_until_complete(run())

    def test_4_stats(self):
        """Test stats query."""
        async def run():
            stats = await db.get_stats()
            self.assertIsNotNone(stats)
            self.assertIn("total_domains", stats)
            self.assertIn("crawled_domains", stats)
            self.assertIn("failed_domains", stats)
            
        self.loop.run_until_complete(run())


if __name__ == "__main__":
    unittest.main()
