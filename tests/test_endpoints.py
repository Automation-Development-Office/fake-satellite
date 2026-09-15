"""
Test suite for Fake Satellite API endpoints.

This script tests all available endpoints to ensure the fake-sat pod
is functioning correctly and can be used for Ansible module testing.
"""

import requests
import json
import sys
from typing import Optional, Dict, Any


BASE_URL = "http://localhost:8000"


class FakeSatelliteTester:
    """Test client for fake-sat API."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.passed = 0
        self.failed = 0
    
    def test_health_checks(self):
        """Test basic health check endpoints."""
        print("\n" + "=" * 70)
        print("HEALTH CHECKS")
        print("=" * 70)
        
        # Test Foreman status
        self._test_endpoint(
            "GET",
            "/api/status",
            expected_status=200,
            description="Foreman API Status"
        )
        
        # Test Katello status
        self._test_endpoint(
            "GET",
            "/katello/api/status",
            expected_status=200,
            description="Katello API Status"
        )
        
        # Test API documentation
        self._test_endpoint(
            "GET",
            "/apidoc/v2.json",
            expected_status=200,
            description="API Documentation"
        )
    
    def test_list_endpoints(self):
        """Test list endpoints for all resources."""
        print("\n" + "=" * 70)
        print("LIST ENDPOINTS")
        print("=" * 70)
        
        resources = [
            ("/api/organizations", "Organizations"),
            ("/api/locations", "Locations"),
            ("/api/hosts", "Hosts"),
            ("/api/hostgroups", "Hostgroups"),
            ("/api/domains", "Domains"),
            ("/api/subnets", "Subnets"),
            ("/api/computeresources", "Compute Resources"),
            ("/api/architectures", "Architectures"),
            ("/api/operatingsystems", "Operating Systems"),
            ("/api/media", "Installation Media"),
            ("/api/ptables", "Partition Tables"),
            ("/api/templates", "Provisioning Templates"),
            ("/api/users", "Users"),
            ("/api/roles", "Roles"),
            ("/api/permissions", "Permissions"),
            ("/api/tasks", "Tasks"),
            ("/katello/api/repositories", "Repositories"),
            ("/katello/api/products", "Products"),
            ("/katello/api/environments", "Environments"),
            ("/katello/api/lifecycle_environments", "Lifecycle Environments"),
            ("/katello/api/content_views", "Content Views"),
            ("/katello/api/activation_keys", "Activation Keys"),
        ]
        
        for endpoint, name in resources:
            self._test_endpoint(
                "GET",
                endpoint,
                expected_status=200,
                description=f"List {name}"
            )
    
    def test_get_by_id(self):
        """Test GET by ID endpoints."""
        print("\n" + "=" * 70)
        print("GET BY ID ENDPOINTS")
        print("=" * 70)
        
        resources = [
            ("/api/organizations/1", "Organization"),
            ("/api/locations/1", "Location"),
            ("/api/hosts/1", "Host"),
            ("/api/hostgroups/1", "Hostgroup"),
            ("/api/domains/1", "Domain"),
            ("/api/subnets/1", "Subnet"),
            ("/api/users/1", "User"),
            ("/api/roles/1", "Role"),
            ("/katello/api/repositories/1", "Repository"),
            ("/katello/api/products/1", "Product"),
        ]
        
        for endpoint, name in resources:
            self._test_endpoint(
                "GET",
                endpoint,
                expected_status=200,
                description=f"Get {name} by ID"
            )
    
    def test_create_resources(self):
        """Test POST (create) endpoints."""
        print("\n" + "=" * 70)
        print("CREATE ENDPOINTS")
        print("=" * 70)
        
        tests = [
            (
                "/api/domains",
                {
                    "domain": {
                        "name": "test-create.local",
                        "fullname": "test-create.local"
                    }
                },
                "Create Domain"
            ),
            (
                "/api/subnets",
                {
                    "subnet": {
                        "name": "Test Subnet",
                        "network": "192.168.50.0",
                        "mask": "255.255.255.0",
                        "gateway": "192.168.50.1"
                    }
                },
                "Create Subnet"
            ),
            (
                "/api/users",
                {
                    "user": {
                        "name": "testuser",
                        "login": "testuser",
                        "email": "testuser@example.com",
                        "firstname": "Test",
                        "lastname": "User",
                        "admin": False
                    }
                },
                "Create User"
            ),
            (
                "/api/organizations",
                {
                    "organization": {
                        "name": "Test Organization"
                    }
                },
                "Create Organization"
            ),
            (
                "/api/locations",
                {
                    "location": {
                        "name": "Test Location"
                    }
                },
                "Create Location"
            ),
            (
                "/katello/api/products",
                {
                    "product": {
                        "name": "Test Product",
                        "organization_id": 1
                    }
                },
                "Create Product"
            ),
        ]
        
        for endpoint, payload, description in tests:
            self._test_endpoint(
                "POST",
                endpoint,
                json_data=payload,
                expected_status=201,
                description=description
            )
    
    def test_update_resources(self):
        """Test PUT (update) endpoints."""
        print("\n" + "=" * 70)
        print("UPDATE ENDPOINTS")
        print("=" * 70)
        
        tests = [
            (
                "/api/organizations/2",
                {"organization": {"name": "Engineering Updated"}},
                "Update Organization"
            ),
            (
                "/api/locations/2",
                {"location": {"name": "US-East Updated"}},
                "Update Location"
            ),
            (
                "/api/users/2",
                {"user": {"email": "updated@example.com"}},
                "Update User"
            ),
        ]
        
        for endpoint, payload, description in tests:
            self._test_endpoint(
                "PUT",
                endpoint,
                json_data=payload,
                expected_status=200,
                description=description
            )
    
    def test_search_filter(self):
        """Test search/filter functionality."""
        print("\n" + "=" * 70)
        print("SEARCH/FILTER ENDPOINTS")
        print("=" * 70)
        
        searches = [
            ("/api/organizations?search=name=\"Default Organization\"", "Search Organizations"),
            ("/api/hosts?search=name~\"web\"", "Filter Hosts by name"),
            ("/api/subnets?search=name=\"Management Network\"", "Search Subnets"),
        ]
        
        for endpoint, description in searches:
            self._test_endpoint(
                "GET",
                endpoint,
                expected_status=200,
                description=description
            )
    
    def test_pagination(self):
        """Test pagination parameters."""
        print("\n" + "=" * 70)
        print("PAGINATION ENDPOINTS")
        print("=" * 70)
        
        self._test_endpoint(
            "GET",
            "/api/organizations?page=1&per_page=10",
            expected_status=200,
            description="Pagination with page and per_page"
        )
    
    def test_sync_operations(self):
        """Test sync endpoints."""
        print("\n" + "=" * 70)
        print("SYNC OPERATIONS")
        print("=" * 70)
        
        # Sync repository
        self._test_endpoint(
            "POST",
            "/katello/api/repositories/1/sync",
            expected_status=200,
            description="Sync Repository"
        )
        
        # Sync product
        self._test_endpoint(
            "POST",
            "/katello/api/products/1/sync",
            expected_status=200,
            description="Sync Product"
        )
    
    def test_associations(self):
        """Test association endpoints."""
        print("\n" + "=" * 70)
        print("ASSOCIATION ENDPOINTS")
        print("=" * 70)
        
        # Add host to hostgroup
        self._test_endpoint(
            "POST",
            "/api/hostgroups/1/hosts/1",
            expected_status=200,
            description="Add Host to Hostgroup"
        )
        
        # Assign host to organization
        self._test_endpoint(
            "POST",
            "/api/organizations/1/hosts/1",
            expected_status=200,
            description="Assign Host to Organization"
        )
        
        # Assign host to location
        self._test_endpoint(
            "POST",
            "/api/locations/1/hosts/1",
            expected_status=200,
            description="Assign Host to Location"
        )
    
    def test_delete_resources(self):
        """Test DELETE endpoints."""
        print("\n" + "=" * 70)
        print("DELETE ENDPOINTS")
        print("=" * 70)
        
        # Note: These should be done last or on resources created during testing
        # Uncomment to test deletion
        
        # self._test_endpoint(
        #     "DELETE",
        #     "/api/domains/1",
        #     expected_status=200,
        #     description="Delete Domain"
        # )
        
        print("  ⊘ Delete tests skipped (use with caution on production data)")
    
    def _test_endpoint(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        expected_status: int = 200,
        description: str = ""
    ) -> bool:
        """
        Test a single endpoint.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            json_data: Request body JSON data
            expected_status: Expected HTTP status code
            description: Test description
        
        Returns:
            True if test passed, False otherwise
        """
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method == "GET":
                response = requests.get(url, timeout=5)
            elif method == "POST":
                response = requests.post(url, json=json_data, timeout=5)
            elif method == "PUT":
                response = requests.put(url, json=json_data, timeout=5)
            elif method == "DELETE":
                response = requests.delete(url, timeout=5)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code == expected_status:
                self.passed += 1
                status_symbol = "✓"
                print(f"  {status_symbol} [{response.status_code}] {description}")
                return True
            else:
                self.failed += 1
                status_symbol = "✗"
                print(
                    f"  {status_symbol} [{response.status_code}] {description} "
                    f"(expected {expected_status})"
                )
                return False
        
        except requests.exceptions.ConnectionError:
            self.failed += 1
            print(f"  ✗ [CONN] {description} (connection refused)")
            return False
        except Exception as e:
            self.failed += 1
            print(f"  ✗ [ERR] {description} ({str(e)})")
            return False
    
    def run_all_tests(self):
        """Run all test suites."""
        print("\n" + "=" * 70)
        print("FAKE SATELLITE API TEST SUITE")
        print("=" * 70)
        print(f"Base URL: {self.base_url}")
        
        try:
            self.test_health_checks()
            self.test_list_endpoints()
            self.test_get_by_id()
            self.test_create_resources()
            self.test_update_resources()
            self.test_search_filter()
            self.test_pagination()
            self.test_sync_operations()
            self.test_associations()
            self.test_delete_resources()
        except KeyboardInterrupt:
            print("\n\nTests interrupted by user")
        
        self._print_summary()
    
    def _print_summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total:  {total}")
        print(f"Passed: {self.passed} ✓")
        print(f"Failed: {self.failed} ✗")
        
        if total > 0:
            percentage = (self.passed / total) * 100
            print(f"Success Rate: {percentage:.1f}%")
        
        print("=" * 70 + "\n")
        
        return self.failed == 0


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test fake-sat API endpoints"
    )
    parser.add_argument(
        "--url",
        default=BASE_URL,
        help=f"Base URL of fake-sat API (default: {BASE_URL})"
    )
    
    args = parser.parse_args()
    
    tester = FakeSatelliteTester(base_url=args.url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
