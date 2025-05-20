import subprocess

def checktests():
    # Run weight tests
    with open("weight_test.log", "w") as f:
        subprocess.run(["pytest", "-v", "weight_test_api.py"], stdout=f, stderr=subprocess.STDOUT)

    # Run billing tests
    with open("billing_test.log", "w") as f:
        subprocess.run(["pytest", "-v", "billing_test_api.py"], stdout=f, stderr=subprocess.STDOUT)

    # Count failures
    failCounter = 0

    with open("billing_test.log", "r") as f:
        if "FAILED" in f.read():
            failCounter += 1

    with open("weight_test.log", "r") as f:
        if "FAILED" in f.read():
            failCounter += 2

    match failCounter:
        case 0:
            print(0, "All tests passed!")
        case 1:
            print(1, "Billing tests failed.")
        case 2:
            print(1, "Weight tests failed.")
        case 3:
            print(1, "Both tests failed.")
        case _:
            print(1, "Unknown result.")

if __name__ == "__main__":
    checktests()
