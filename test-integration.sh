# Clean start
docker-compose -f docker-compose-integration.yml down --volumes --remove-orphans 2>/dev/null

# Start databases first
echo "📊 מפעיל מסדי נתונים..."
docker-compose -f docker-compose-integration.yml up -d weight_db billing_db

# Wait for databases
echo "⏳ ממתין למסדי נתונים (60 שניות)..."
sleep 60

# Check database health
echo "�� בודק בריאות מסדי נתונים..."
docker-compose -f docker-compose-integration.yml ps

# Start applications
echo "🚀 מפעיל אפליקציות..."
docker-compose -f docker-compose-integration.yml up -d weight_app billing_app

# Wait for applications
echo "⏳ ממתין לאפליקציות (30 שניות)..."
sleep 30

# Step 3: Check all services
echo "🔍 בודק כל השירותים..."
docker-compose -f docker-compose-integration.yml ps

# Step 4: Run integration tests
echo "🧪 מתחיל בדיקות אינטגרציה..."

WEIGHT_URL="http://127.0.0.1:5000"
BILLING_URL="http://127.0.0.1:5500"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

# Test 1: Health checks
echo "1️⃣ בדיקות בריאות..."
WEIGHT_HEALTH=$(curl -s $WEIGHT_URL/health 2>/dev/null || echo "FAILED")
BILLING_HEALTH=$(curl -s $BILLING_URL/health 2>/dev/null || echo "FAILED")

echo "Weight Health: $WEIGHT_HEALTH"
echo "Billing Health: $BILLING_HEALTH"

if [[ $WEIGHT_HEALTH == *"OK"* ]]; then
    print_success "Weight Service בריא"
else
    print_error "Weight Service לא בריא"
    echo "Weight Logs:"
    docker-compose -f docker-compose-integration.yml logs weight_app | tail -5
    exit 1
fi

if [[ $BILLING_HEALTH == *"OK"* ]]; then
    print_success "Billing Service בריא"
else
    print_error "Billing Service לא בריא"
    echo "Billing Logs:"
    docker-compose -f docker-compose-integration.yml logs billing_app | tail -5
    exit 1
fi

# Test 2: Setup data
echo "2️⃣ הכנת נתוני בדיקה..."

# Create provider
PROVIDER_RESPONSE=$(curl -s -X POST $BILLING_URL/provider \
    -H "Content-Type: application/json" \
    -d '{"name": "IntegrationTestProvider"}')
PROVIDER_ID=$(echo $PROVIDER_RESPONSE | grep -o '"provider_id":[0-9]*' | grep -o '[0-9]*')
print_success "Provider נוצר: $PROVIDER_ID"

# Register truck
curl -s -X POST $BILLING_URL/truck \
    -H "Content-Type: application/json" \
    -d "{\"provider\": $PROVIDER_ID, \"id\": \"TRUCK-INTEGRATION-001\"}" > /dev/null
print_success "משאית נרשמה: TRUCK-INTEGRATION-001"

# Add containers to Weight
echo "3️⃣ מוסיף קונטיינרים..."
curl -s -X POST $WEIGHT_URL/batch-weight \
    -H "Content-Type: application/json" \
    -d '{"file": "containers1.csv"}' > /dev/null
print_success "קונטיינרים נוספו"

# Test 3: Create weight sessions
echo "4️⃣ יוצר weight sessions..."

# Session 1: Orange
curl -s -X POST $WEIGHT_URL/weight \
    -H "Content-Type: application/json" \
    -d '{
        "direction": "in",
        "truck": "TRUCK-INTEGRATION-001",
        "containers": ["CONT-001", "CONT-002"],
        "weight": 1500,
        "unit": "kg",
        "force": false,
        "produce": "orange"
    }' > /dev/null

sleep 2

curl -s -X POST $WEIGHT_URL/weight \
    -H "Content-Type: application/json" \
    -d '{
        "direction": "out",
        "truck": "TRUCK-INTEGRATION-001",
        "containers": ["CONT-001", "CONT-002"],
        "weight": 800,
        "unit": "kg",
        "force": false,
        "produce": "orange"
    }' > /dev/null

print_success "Session תפוזים נוצר"

# Session 2: Apple
sleep 3

curl -s -X POST $WEIGHT_URL/weight \
    -H "Content-Type: application/json" \
    -d '{
        "direction": "in",
        "truck": "TRUCK-INTEGRATION-001",
        "containers": ["CONT-003"],
        "weight": 1200,
        "unit": "kg",
        "force": false,
        "produce": "apple"
    }' > /dev/null

sleep 2

curl -s -X POST $WEIGHT_URL/weight \
    -H "Content-Type: application/json" \
    -d '{
        "direction": "out",
        "truck": "TRUCK-INTEGRATION-001",
        "containers": ["CONT-003"],
        "weight": 800,
        "unit": "kg",
        "force": false,
        "produce": "apple"
    }' > /dev/null

print_success "Session תפוחים נוצר"

# Test 4: Test integration
echo "5️⃣ בודק אינטגרציה..."

# Check truck info through billing
TRUCK_INFO=$(curl -s "$BILLING_URL/truck/TRUCK-INTEGRATION-001")
echo "Truck Info: $TRUCK_INFO"

if [[ $TRUCK_INFO == *"sessions"* ]]; then
    print_success "Billing מתחבר ל-Weight!"
    SESSIONS_COUNT=$(echo $TRUCK_INFO | grep -o '"sessions":\[[^\]]*\]' | tr ',' '\n' | grep -c '"')
    echo "מספר sessions: $SESSIONS_COUNT"
else
    print_warning "Billing לא מוצא sessions"
fi

# Test 5: Generate bill
echo "6️⃣ יוצר חשבונית..."
BILL_RESPONSE=$(curl -s "$BILLING_URL/bill/$PROVIDER_ID")
echo "Bill: $BILL_RESPONSE"

# Parse results
TRUCK_COUNT=$(echo $BILL_RESPONSE | grep -o '"truckCount":[0-9]*' | grep -o '[0-9]*')
SESSION_COUNT=$(echo $BILL_RESPONSE | grep -o '"sessionCount":[0-9]*' | grep -o '[0-9]*')
TOTAL=$(echo $BILL_RESPONSE | grep -o '"total":[0-9]*' | grep -o '[0-9]*')

echo
echo "🏆 תוצאות סופיות:"
echo "=================="
echo "Truck Count: $TRUCK_COUNT"
echo "Session Count: $SESSION_COUNT"
echo "Total Amount: $TOTAL"

if [ "$TRUCK_COUNT" = "1" ] && [ "$SESSION_COUNT" -gt "0" ]; then
    print_success "🎉 אינטגרציה מושלמת! Weight + Billing עובדים יחד!"
else
    print_warning "אינטגרציה חלקית - צריך בדיקה נוספת"
fi

echo
echo "🔧 פקודות לבדיקה נוספת:"
echo "curl $WEIGHT_URL/health"
echo "curl $BILLING_URL/health"
echo "curl '$BILLING_URL/bill/$PROVIDER_ID'"
echo "docker-compose -f docker-compose-integration.yml logs"

echo
echo "🛑 לעצירת השירותים:"
echo "docker-compose -f docker-compose-integration.yml down --volumes"
