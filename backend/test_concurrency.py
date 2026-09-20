import json
import urllib.request
import concurrent.futures

BASE_URL = "http://127.0.0.1:8000"


def send_chat(message: str, session_id: str) -> dict:
    url = f"{BASE_URL}/api/chat"
    payload = json.dumps({"message": message, "sessionId": session_id}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def run_tests():
    print("=== TEST 1: Cancel any existing bookings to ensure clean starting state ===")
    send_chat("Cancel my appointment.", "user-A")
    send_chat("Cancel my appointment.", "user-B")

    print("\n=== TEST 2: Concurrent Booking for the Same Slot (Dr. Ravi at 6 PM) ===")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(send_chat, "Book Dr. Ravi tomorrow at 6 PM", "user-A")
        f2 = executor.submit(send_chat, "Book Dr. Ravi tomorrow at 6 PM", "user-B")
        res1 = f1.result()
        res2 = f2.result()

    print("\n--- User A Response ---")
    print("Message:", res1.get("message"))
    actions1 = [a.get("type") or a.get("action") for a in res1.get("actions", [])]
    print("Actions:", actions1)

    print("\n--- User B Response ---")
    print("Message:", res2.get("message"))
    actions2 = [a.get("type") or a.get("action") for a in res2.get("actions", [])]
    print("Actions:", actions2)

    # Validate that one succeeded and one received collision/alternatives
    has_booked_1 = "BOOK_APPOINTMENT" in actions1
    has_booked_2 = "BOOK_APPOINTMENT" in actions2

    print(f"\nUser A Booked: {has_booked_1}, User B Booked: {has_booked_2}")
    assert (has_booked_1 and not has_booked_2) or (has_booked_2 and not has_booked_1), \
        "Concurrency failure: exactly one user must book the slot!"
    print("SUCCESS: Exactly one user was granted the slot, preventing double-booking!")

    # Verify that the conflicting user received alternative slots and SHOW_SLOTS action
    conflicted_res = res2 if has_booked_1 else res1
    conflicted_actions = actions2 if has_booked_1 else actions1
    assert "SHOW_SLOTS" in conflicted_actions, "Conflicted user must receive SHOW_SLOTS action!"
    assert "no longer available" in conflicted_res["message"] or "already booked" in conflicted_res["message"]
    print("SUCCESS: Conflicted user received clear collision explanation and real-time alternative slots!")

    print("\n=== TEST 3: Slot Revalidation & Real-Time Availability Check ===")
    # Query Dr. Ravi's slots again
    query_res = send_chat("What are Dr. Ravi slots tomorrow?", "user-C")
    slots_action = next((a for a in query_res.get("actions", []) if (a.get("type") == "SHOW_SLOTS" or a.get("action") == "SHOW_SLOTS")), None)
    if slots_action:
        ravi_slots = [s for s in slots_action.get("payload", {}).get("slots", []) if "ravi" in s.get("doctor", "").lower()]
        avail_times = [s["time"] for s in ravi_slots if s.get("isAvailable", True)]
        print("Available times for Dr. Ravi:", avail_times)
        assert "6:00 PM" not in avail_times, "6:00 PM must not be available after booking!"
        print("SUCCESS: 6:00 PM is correctly absent from real-time available slots!")

    print("\n=== TEST 4: Cancellation & Cache Invalidation ===")
    winner_session = "user-A" if has_booked_1 else "user-B"
    cancel_res = send_chat("Cancel my appointment.", winner_session)
    print("Cancel Response:", cancel_res.get("message"))
    assert "CANCEL_APPOINTMENT" in [a.get("type") or a.get("action") for a in cancel_res.get("actions", [])]

    # Re-query availability to verify the slot is freed up
    query_after_cancel = send_chat("What are Dr. Ravi slots tomorrow?", "user-C")
    slots_action2 = next((a for a in query_after_cancel.get("actions", []) if (a.get("type") == "SHOW_SLOTS" or a.get("action") == "SHOW_SLOTS")), None)
    if slots_action2:
        ravi_slots2 = [s for s in slots_action2.get("payload", {}).get("slots", []) if "ravi" in s.get("doctor", "").lower()]
        avail_times2 = [s["time"] for s in ravi_slots2 if s.get("isAvailable", True)]
        print("Available times after cancellation:", avail_times2)
        assert "6:00 PM" in avail_times2, "6:00 PM must be available again after cancellation!"
        print("SUCCESS: 6:00 PM is immediately available again after cancellation!")

    print("\nALL REAL-TIME AVAILABILITY & CONCURRENCY TESTS PASSED!")


if __name__ == "__main__":
    run_tests()
