#!/bin/bash

# Quick test script for fake-sat API using curl
# Usage: ./tests/quick_test.sh [base_url]

set -e

BASE_URL="${1:-http://localhost:8000}"
PASS=0
FAIL=0

echo "========================================================================"
echo "FAKE SATELLITE QUICK TEST"
echo "========================================================================"
echo "Base URL: $BASE_URL"
echo

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local data=$4
    local expected_status=${5:-200}
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" -H "Content-Type: application/json" -d "$data" "$BASE_URL$endpoint")
    fi
    
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$status_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓${NC} [$status_code] $description"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} [$status_code] $description (expected $expected_status)"
        ((FAIL++))
    fi
}

echo "------- Health Checks -------"
test_endpoint GET "/api/status" "Foreman Status"
test_endpoint GET "/katello/api/status" "Katello Status"
test_endpoint GET "/apidoc/v2.json" "API Documentation"

echo
echo "------- List Endpoints -------"
test_endpoint GET "/api/organizations" "List Organizations"
test_endpoint GET "/api/locations" "List Locations"
test_endpoint GET "/api/hosts" "List Hosts"
test_endpoint GET "/api/users" "List Users"
test_endpoint GET "/api/domains" "List Domains"
test_endpoint GET "/api/subnets" "List Subnets"
test_endpoint GET "/katello/api/repositories" "List Repositories"
test_endpoint GET "/katello/api/products" "List Products"

echo
echo "------- Get by ID -------"
test_endpoint GET "/api/organizations/1" "Get Organization"
test_endpoint GET "/api/hosts/1" "Get Host"
test_endpoint GET "/api/users/1" "Get User"
test_endpoint GET "/katello/api/repositories/1" "Get Repository"

echo
echo "------- Search/Filter -------"
test_endpoint GET "/api/organizations?search=name=%22Default%20Organization%22" "Search Organizations"
test_endpoint GET "/api/hosts?search=name~%22web%22" "Filter Hosts"

echo
echo "------- Create Resource -------"
test_endpoint POST "/api/domains" \
    "Create Domain" \
    '{"domain":{"name":"test.local","fullname":"test.local"}}' \
    "201"

echo
echo "------- Sync Operations -------"
test_endpoint POST "/katello/api/repositories/1/sync" "Sync Repository" "{}" "200"
test_endpoint POST "/katello/api/products/1/sync" "Sync Product" "{}" "200"

echo
echo "------- Association Operations -------"
test_endpoint POST "/api/hostgroups/1/hosts/1" "Add Host to Hostgroup" "{}" "200"
test_endpoint POST "/api/organizations/1/hosts/1" "Assign Host to Organization" "{}" "200"

echo
echo "========================================================================"
echo "SUMMARY"
echo "========================================================================"
echo -e "Passed: ${GREEN}$PASS ✓${NC}"
echo -e "Failed: ${RED}$FAIL ✗${NC}"

total=$((PASS + FAIL))
if [ $total -gt 0 ]; then
    percentage=$((PASS * 100 / total))
    echo "Success Rate: $percentage%"
fi
echo "========================================================================"

if [ $FAIL -eq 0 ]; then
    exit 0
else
    exit 1
fi
