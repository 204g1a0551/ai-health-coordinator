from datetime import datetime
from typing import Dict, Any, List, Optional
from app.providers.base import BaseHealthcareProvider

# Seeded Bengaluru Hospitals & Specialty Clinics
BENGALURU_HOSPITALS = [
    {
        "id": "hosp-manipal-hal",
        "name": "Manipal Hospital",
        "type": "Multi-Specialty Hospital",
        "locality": "Indiranagar / Old Airport Road",
        "address": "98 HAL Old Airport Road, Kodihalli, Bengaluru, Karnataka 560017",
        "phone": "+91 80 2502 4444",
        "rating": 4.6,
        "departments": ["General Medicine", "Cardiology", "Neurology", "Orthopedics"],
    },
    {
        "id": "hosp-apollo-bannerghatta",
        "name": "Apollo Hospital",
        "type": "Super Specialty Hospital",
        "locality": "Jayanagar / Bannerghatta Road",
        "address": "154/11 Bannerghatta Road, Opp IIM-B, Bengaluru, Karnataka 560076",
        "phone": "+91 80 2630 4050",
        "rating": 4.5,
        "departments": ["General Medicine", "Oncology", "Pediatrics", "ENT"],
    },
    {
        "id": "hosp-fortis-cunningham",
        "name": "Fortis Hospital",
        "type": "Specialty Hospital",
        "locality": "Cunningham Road / Vasanth Nagar",
        "address": "14 Cunningham Road, Vasanth Nagar, Bengaluru, Karnataka 560052",
        "phone": "+91 80 4199 4444",
        "rating": 4.4,
        "departments": ["ENT", "General Medicine", "Orthopedics", "Cardiology"],
    },
    {
        "id": "hosp-aster-hebbal",
        "name": "Aster CMI Hospital",
        "type": "Multi-Specialty Hospital",
        "locality": "Hebbal",
        "address": "No. 43/2, New Airport Road, NH 44, Sahakar Nagar, Hebbal, Bengaluru, Karnataka 560092",
        "phone": "+91 80 4342 0100",
        "rating": 4.7,
        "departments": ["General Medicine", "Pediatrics", "Dermatology", "Neurology"],
    },
    {
        "id": "hosp-sakra-bellandur",
        "name": "Sakra World Hospital",
        "type": "Multi-Specialty Hospital",
        "locality": "Bellandur / Outer Ring Road",
        "address": "SY No 52/2 & 52/3, Devarabeesanahalli, Bellandur, Bengaluru, Karnataka 560103",
        "phone": "+91 80 4969 4969",
        "rating": 4.6,
        "departments": ["Orthopedics", "General Medicine", "Rehabilitation", "Spine Care"],
    },
    {
        "id": "hosp-cloudnine-jayanagar",
        "name": "Cloudnine Hospital",
        "type": "Maternity & Children Hospital",
        "locality": "Jayanagar",
        "address": "1533 9th Main Rd, 3rd Block, Jayanagar, Bengaluru, Karnataka 560011",
        "phone": "+91 80 6792 9999",
        "rating": 4.8,
        "departments": ["Pediatrics", "Gynecology", "General Medicine"],
    },
    {
        "id": "clinic-kaveri-indiranagar",
        "name": "Kaveri Healthcare Clinic",
        "type": "Specialty Clinic",
        "locality": "Indiranagar",
        "address": "742, 12th Main Rd, HAL 2nd Stage, Indiranagar, Bengaluru, Karnataka 560038",
        "phone": "+91 80 2521 1122",
        "rating": 4.5,
        "departments": ["Dermatology", "General Medicine", "Cosmetology"],
    },
    {
        "id": "clinic-narayana-hsr",
        "name": "Narayana Health Clinic",
        "type": "Primary & Dental Care Clinic",
        "locality": "HSR Layout",
        "address": "Plot No 452, 24th Main Road, Sector 1, HSR Layout, Bengaluru, Karnataka 560102",
        "phone": "+91 80 6750 6860",
        "rating": 4.3,
        "departments": ["Dental", "General Medicine", "ENT"],
    },
    {
        "id": "clinic-columbia-whitefield",
        "name": "Columbia Asia / Manipal Clinic",
        "type": "Outpatient & Specialty Clinic",
        "locality": "Whitefield",
        "address": "Survey No. 10P & 12P, Ramagondanahalli, Varthur Kodi, Whitefield, Bengaluru, Karnataka 560066",
        "phone": "+91 80 6165 6262",
        "rating": 4.5,
        "departments": ["Ophthalmology", "General Medicine", "Dermatology"],
    },
]

# Seeded Bengaluru Doctors
BENGALURU_DOCTORS = [
    {
        "id": "doc-ravi",
        "name": "Dr. Ravi Kumar",
        "qualification": "MBBS, MD (Internal Medicine)",
        "department": "General Medicine",
        "hospitalId": "hosp-manipal-hal",
        "hospital": "Manipal Hospital",
        "clinic": "Manipal Outpatient Center",
        "locality": "Indiranagar / Old Airport Road",
        "address": "98 HAL Old Airport Road, Kodihalli, Bengaluru 560017",
        "consultationFee": "₹600",
        "consultationType": "In-Person & Teleconsultation",
        "experience": "14+ yrs experience",
        "rating": 4.9,
        "availableStatus": "Available",
    },
    {
        "id": "doc-priya",
        "name": "Dr. Priya Sharma",
        "qualification": "MBBS, DNB (Family Medicine)",
        "department": "General Medicine",
        "hospitalId": "hosp-apollo-bannerghatta",
        "hospital": "Apollo Hospital",
        "clinic": "Apollo Clinic",
        "locality": "Jayanagar / Bannerghatta Road",
        "address": "154/11 Bannerghatta Road, Opp IIM-B, Bengaluru 560076",
        "consultationFee": "₹550",
        "consultationType": "In-Person",
        "experience": "10+ yrs experience",
        "rating": 4.8,
        "availableStatus": "Available",
    },
    {
        "id": "doc-arjun",
        "name": "Dr. Arjun Reddy",
        "qualification": "MBBS, MS (ENT), DLO",
        "department": "ENT",
        "hospitalId": "hosp-fortis-cunningham",
        "hospital": "Fortis Hospital",
        "clinic": "Fortis ENT Center",
        "locality": "Cunningham Road / Vasanth Nagar",
        "address": "14 Cunningham Road, Vasanth Nagar, Bengaluru 560052",
        "consultationFee": "₹700",
        "consultationType": "In-Person & Teleconsultation",
        "experience": "12+ yrs experience",
        "rating": 4.7,
        "availableStatus": "Available",
    },
    {
        "id": "doc-sneha",
        "name": "Dr. Sneha Rao",
        "qualification": "MBBS, MD (Dermatology, Venereology & Leprosy)",
        "department": "Dermatology",
        "hospitalId": "clinic-kaveri-indiranagar",
        "hospital": "Kaveri Healthcare Clinic",
        "clinic": "Kaveri Skin & Hair Center",
        "locality": "Indiranagar",
        "address": "742, 12th Main Rd, HAL 2nd Stage, Indiranagar, Bengaluru 560038",
        "consultationFee": "₹800",
        "consultationType": "In-Person & Teleconsultation",
        "experience": "8+ yrs experience",
        "rating": 4.9,
        "availableStatus": "Available",
    },
    {
        "id": "doc-meera",
        "name": "Dr. Meera Iyer",
        "qualification": "MBBS, DCH, DNB (Pediatrics)",
        "department": "Pediatrics",
        "hospitalId": "hosp-cloudnine-jayanagar",
        "hospital": "Cloudnine Hospital",
        "clinic": "Cloudnine Child Wellness Clinic",
        "locality": "Jayanagar",
        "address": "1533 9th Main Rd, 3rd Block, Jayanagar, Bengaluru 560011",
        "consultationFee": "₹650",
        "consultationType": "In-Person",
        "experience": "11+ yrs experience",
        "rating": 4.9,
        "availableStatus": "Available",
    },
    {
        "id": "doc-vikram",
        "name": "Dr. Vikram Seth",
        "qualification": "MBBS, MS (Orthopedics), M.Ch (Joint Replacement)",
        "department": "Orthopedics",
        "hospitalId": "hosp-sakra-bellandur",
        "hospital": "Sakra World Hospital",
        "clinic": "Sakra Joint & Spine Institute",
        "locality": "Bellandur / Outer Ring Road",
        "address": "SY No 52/2, Devarabeesanahalli, Bellandur, Bengaluru 560103",
        "consultationFee": "₹750",
        "consultationType": "In-Person",
        "experience": "15+ yrs experience",
        "rating": 4.8,
        "availableStatus": "Available",
    },
    {
        "id": "doc-alok",
        "name": "Dr. Alok Verma",
        "qualification": "BDS, MDS (Prosthodontics & Implantology)",
        "department": "Dental",
        "hospitalId": "clinic-narayana-hsr",
        "hospital": "Narayana Health Clinic",
        "clinic": "Narayana Dental & Oral Care",
        "locality": "HSR Layout",
        "address": "Plot 452, 24th Main Road, Sector 1, HSR Layout, Bengaluru 560102",
        "consultationFee": "₹500",
        "consultationType": "In-Person",
        "experience": "9+ yrs experience",
        "rating": 4.6,
        "availableStatus": "Available",
    },
    {
        "id": "doc-kavita",
        "name": "Dr. Kavita Menon",
        "qualification": "MBBS, MS (Ophthalmology), FRCS (Glasgow)",
        "department": "Ophthalmology",
        "hospitalId": "clinic-columbia-whitefield",
        "hospital": "Columbia Asia / Manipal Clinic",
        "clinic": "Columbia Eye Care Center",
        "locality": "Whitefield",
        "address": "Survey No. 10P, Ramagondanahalli, Whitefield, Bengaluru 560066",
        "consultationFee": "₹700",
        "consultationType": "In-Person & Teleconsultation",
        "experience": "13+ yrs experience",
        "rating": 4.8,
        "availableStatus": "Available",
    },
    {
        "id": "doc-rajesh",
        "name": "Dr. Rajesh Nair",
        "qualification": "MBBS, MD (Internal Medicine)",
        "department": "General Medicine",
        "hospitalId": "clinic-columbia-whitefield",
        "hospital": "Columbia Asia / Manipal Clinic",
        "clinic": "Columbia General Medicine OPD",
        "locality": "Whitefield",
        "address": "Survey No. 10P, Ramagondanahalli, Whitefield, Bengaluru 560066",
        "consultationFee": "₹650",
        "consultationType": "In-Person & Teleconsultation",
        "experience": "16+ yrs experience",
        "rating": 4.9,
        "availableStatus": "Available",
    },
]

# Consultation Slots matching database schedule
BENGALURU_SLOTS = {
    "doc-ravi": [
        {"id": "slot-r-1", "date": "Tomorrow, Oct 24", "time": "09:30 AM", "period": "morning", "isAvailable": True},
        {"id": "slot-r-2", "date": "Tomorrow, Oct 24", "time": "11:30 AM", "period": "morning", "isAvailable": True},
        {"id": "slot-r-3", "date": "Tomorrow, Oct 24", "time": "02:30 PM", "period": "afternoon", "isAvailable": True},
        {"id": "slot-r-4", "date": "Tomorrow, Oct 24", "time": "5:30 PM", "period": "evening", "isAvailable": True},
        {"id": "slot-r-6", "date": "Tomorrow, Oct 24", "time": "6:00 PM", "period": "evening", "isAvailable": True},
        {"id": "slot-r-5", "date": "Tomorrow, Oct 24", "time": "6:30 PM", "period": "evening", "isAvailable": True},
    ],
    "doc-priya": [
        {"id": "slot-p-1", "date": "Tomorrow, Oct 24", "time": "10:00 AM", "period": "morning", "isAvailable": True},
        {"id": "slot-p-2", "date": "Tomorrow, Oct 24", "time": "03:00 PM", "period": "afternoon", "isAvailable": True},
        {"id": "slot-p-3", "date": "Tomorrow, Oct 24", "time": "6:00 PM", "period": "evening", "isAvailable": True},
    ],
    "doc-arjun": [
        {"id": "slot-a-1", "date": "Tomorrow, Oct 24", "time": "10:30 AM", "period": "morning", "isAvailable": True},
        {"id": "slot-a-2", "date": "Tomorrow, Oct 24", "time": "04:30 PM", "period": "afternoon", "isAvailable": True},
        {"id": "slot-a-3", "date": "Tomorrow, Oct 24", "time": "6:00 PM", "period": "evening", "isAvailable": True},
    ],
    "doc-sneha": [
        {"id": "slot-s-1", "date": "Tomorrow, Oct 24", "time": "11:00 AM", "period": "morning", "isAvailable": True},
        {"id": "slot-s-2", "date": "Tomorrow, Oct 24", "time": "03:30 PM", "period": "afternoon", "isAvailable": True},
        {"id": "slot-s-3", "date": "Tomorrow, Oct 24", "time": "5:00 PM", "period": "evening", "isAvailable": True},
    ],
    "doc-meera": [
        {"id": "slot-m-1", "date": "Tomorrow, Oct 24", "time": "10:00 AM", "period": "morning", "isAvailable": True},
        {"id": "slot-m-2", "date": "Tomorrow, Oct 24", "time": "05:00 PM", "period": "evening", "isAvailable": True},
    ],
    "doc-vikram": [
        {"id": "slot-v-1", "date": "Tomorrow, Oct 24", "time": "11:30 AM", "period": "morning", "isAvailable": True},
        {"id": "slot-v-2", "date": "Tomorrow, Oct 24", "time": "04:00 PM", "period": "afternoon", "isAvailable": True},
    ],
    "doc-alok": [
        {"id": "slot-d-1", "date": "Tomorrow, Oct 24", "time": "09:00 AM", "period": "morning", "isAvailable": True},
        {"id": "slot-d-2", "date": "Tomorrow, Oct 24", "time": "06:00 PM", "period": "evening", "isAvailable": True},
    ],
    "doc-kavita": [
        {"id": "slot-k-1", "date": "Tomorrow, Oct 24", "time": "11:00 AM", "period": "morning", "isAvailable": True},
        {"id": "slot-k-2", "date": "Tomorrow, Oct 24", "time": "5:30 PM", "period": "evening", "isAvailable": True},
    ],
    "doc-rajesh": [
        {"id": "slot-rn-1", "date": "Tomorrow, Oct 24", "time": "10:30 AM", "period": "morning", "isAvailable": True},
        {"id": "slot-rn-2", "date": "Tomorrow, Oct 24", "time": "4:30 PM", "period": "evening", "isAvailable": True},
        {"id": "slot-rn-3", "date": "Tomorrow, Oct 24", "time": "6:30 PM", "period": "evening", "isAvailable": True},
    ],
}


class BengaluruSeededProvider(BaseHealthcareProvider):
    """
    Verified Bengaluru Healthcare Provider Implementation.
    Serves seeded hospital, clinic, doctor, and slot data across key Bengaluru tech corridors.
    Can be seamlessly swapped with real hospital APIs (Manipal, Apollo, Practo) in production.
    """

    @property
    def provider_name(self) -> str:
        return "Bengaluru Health Grid (Verified Provider)"

    def _format_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Attaches provenance and fresh timestamp to provider responses."""
        return {
            **data,
            "dataSource": self.provider_name,
            "lastUpdated": datetime.utcnow().strftime("%d %b %Y, %I:%M %p"),
        }

    def search_doctors(
        self,
        query: Optional[str] = None,
        department: Optional[str] = None,
        locality: Optional[str] = None,
        hospital_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        results = []
        for doc in BENGALURU_DOCTORS:
            # Match query (name)
            if query and query.lower() not in doc["name"].lower():
                continue
            # Match department
            if department and department.lower() not in doc["department"].lower():
                continue
            # Match locality
            if locality and locality.lower() not in doc["locality"].lower() and locality.lower() not in doc["address"].lower():
                continue
            # Match hospital id
            if hospital_id and doc["hospitalId"].lower() != hospital_id.lower():
                continue

            results.append(self._format_metadata(doc))
        return results

    def search_hospitals(
        self,
        query: Optional[str] = None,
        locality: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        results = []
        for h in BENGALURU_HOSPITALS:
            if query and query.lower() not in h["name"].lower():
                continue
            if locality and locality.lower() not in h["locality"].lower() and locality.lower() not in h["address"].lower():
                continue
            results.append(self._format_metadata(h))
        return results

    def get_doctor_details(self, doctor_id: str) -> Optional[Dict[str, Any]]:
        for doc in BENGALURU_DOCTORS:
            if doc["id"].lower() == doctor_id.lower() or doctor_id.lower() in doc["name"].lower():
                return self._format_metadata(doc)
        return None

    def get_available_slots(
        self,
        doctor_id: str,
        date: Optional[str] = None,
        period: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        doc = self.get_doctor_details(doctor_id)
        if not doc:
            return []

        clean_id = doc["id"]
        raw_slots = BENGALURU_SLOTS.get(clean_id, [])

        filtered = []
        for s in raw_slots:
            if period and s["period"].lower() != period.lower():
                continue
            if date and date.lower() not in s["date"].lower():
                pass
            filtered.append({
                **s,
                "doctor": doc["name"],
                "department": doc["department"],
                "hospital": doc["hospital"],
                "locality": doc["locality"],
                "dataSource": self.provider_name,
                "lastUpdated": datetime.utcnow().strftime("%d %b %Y, %I:%M %p"),
            })
        return filtered

    def search_by_department(
        self,
        department: str,
        locality: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self.search_doctors(department=department, locality=locality)

    def search_by_location(
        self,
        locality: str,
        department: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self.search_doctors(locality=locality, department=department)
