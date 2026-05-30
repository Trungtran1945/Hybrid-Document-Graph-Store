"""
Synthetic Medical Data Generator for Hybrid Document-Graph Store.
Generates Patient_Symptoms (documents) and Disease_Correlations (graph).
"""
import random
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
from faker import Faker
from ..core.config import config
from ..core.models import (
    PatientSymptom, GraphNode, GraphEdge,
    NodeType, EdgeType
)

fake = Faker()


# ============================================================
# Medical Knowledge Data
# ============================================================

MEDICAL_FIELDS = [
    "Cardiology", "Neurology", "Oncology", "Pulmonology",
    "Gastroenterology", "Orthopedics", "Infectious_Disease",
    "Endocrinology", "Nephrology", "Rheumatology"
]

DISEASES = {
    "Cardiology": [
        ("Hypertension", ["headache", "dizziness", "shortness of breath", "chest pain", "fatigue"]),
        ("Arrhythmia", ["palpitations", "lightheadedness", "fainting", "fatigue", "shortness of breath"]),
        ("Coronary_Artery_Disease", ["chest pain", "shortness of breath", "fatigue", "nausea"]),
        ("Heart_Failure", ["fatigue", "shortness of breath", "swelling", "cough", "weight gain"]),
        ("Atrial_Fibrillation", ["palpitations", "fatigue", "dizziness", "shortness of breath"]),
        ("Myocarditis", ["chest pain", "fatigue", "shortness of breath", "fever", "joint pain"]),
    ],
    "Neurology": [
        ("Migraine", ["severe headache", "nausea", "sensitivity to light", "visual disturbances", "dizziness"]),
        ("Epilepsy", ["seizures", "confusion", "staring", "muscle jerking", "loss of consciousness"]),
        ("Parkinson_Disease", ["tremor", "stiffness", "slow movement", "balance problems", "speech changes"]),
        ("Multiple_Sclerosis", ["numbness", "weakness", "vision problems", "fatigue", "balance issues"]),
        ("Stroke", ["face drooping", "arm weakness", "speech difficulty", "confusion", "vision loss"]),
        ("Alzheimer_Disease", ["memory loss", "confusion", "disorientation", "behavior changes", "language problems"]),
    ],
    "Oncology": [
        ("Lung_Cancer", ["persistent cough", "coughing blood", "chest pain", "weight loss", "fatigue"]),
        ("Breast_Cancer", ["breast lump", "skin changes", "nipple discharge", "breast pain", "swelling"]),
        ("Colorectal_Cancer", ["rectal bleeding", "abdominal pain", "change in bowel habits", "weight loss", "fatigue"]),
        ("Prostate_Cancer", ["urinary problems", "blood in urine", "pelvic pain", "bone pain", "erectile dysfunction"]),
        ("Leukemia", ["fatigue", "frequent infections", "easy bruising", "weight loss", "night sweats"]),
    ],
    "Pulmonology": [
        ("COPD", ["chronic cough", "shortness of breath", "wheezing", "mucus production", "fatigue"]),
        ("Asthma", ["wheezing", "shortness of breath", "chest tightness", "coughing", "difficulty sleeping"]),
        ("Pneumonia", ["high fever", "cough", "chest pain", "shortness of breath", "fatigue"]),
        ("Pulmonary_Embolism", ["sudden shortness of breath", "chest pain", "cough", "lightheadedness", "rapid heartbeat"]),
        ("Tuberculosis", ["chronic cough", "coughing blood", "night sweats", "weight loss", "fever"]),
    ],
    "Gastroenterology": [
        ("GERD", ["heartburn", "acid reflux", "difficulty swallowing", "chronic cough", "chest pain"]),
        ("Peptic_Ulcer", ["stomach pain", "nausea", "indigestion", "bloating", "loss of appetite"]),
        ("Crohn_Disease", ["abdominal pain", "diarrhea", "weight loss", "fatigue", "blood in stool"]),
        ("Hepatitis_B", ["jaundice", "fatigue", "abdominal pain", "nausea", "dark urine"]),
        ("Gallstones", ["abdominal pain", "jaundice", "nausea", "fever", "back pain"]),
    ],
    "Orthopedics": [
        ("Osteoarthritis", ["joint pain", "stiffness", "swelling", "decreased flexibility", "grinding sensation"]),
        ("Rheumatoid_Arthritis", ["joint swelling", "joint pain", "fatigue", "fever", "joint deformity"]),
        ("Osteoporosis", ["bone fractures", "back pain", "stooped posture", "loss of height", "bone pain"]),
        ("Herniated_Disc", ["back pain", "leg pain", "numbness", "muscle weakness", "tingling"]),
        ("Fracture", ["severe pain", "swelling", "deformity", "inability to move", "bruising"]),
    ],
    "Infectious_Disease": [
        ("COVID_19", ["fever", "cough", "shortness of breath", "loss of taste", "fatigue"]),
        ("Dengue_Fever", ["high fever", "severe headache", "joint pain", "rash", "fatigue"]),
        ("Malaria", ["fever", "chills", "sweating", "headache", "nausea"]),
        ("Typhoid", ["high fever", "abdominal pain", "rash", "weakness", "headache"]),
        ("HIV_AIDS", ["fever", "weight loss", "fatigue", "night sweats", "opportunistic infections"]),
    ],
    "Endocrinology": [
        ("Diabetes_Type_2", ["increased thirst", "frequent urination", "fatigue", "blurred vision", "slow healing"]),
        ("Hypothyroidism", ["fatigue", "weight gain", "cold sensitivity", "constipation", "dry skin"]),
        ("Hyperthyroidism", ["weight loss", "rapid heartbeat", "tremor", "anxiety", "heat sensitivity"]),
        ("Cushing_Syndrome", ["weight gain", "moon face", "high blood pressure", "easy bruising", "fatigue"]),
        ("Addison_Disease", ["fatigue", "low blood pressure", "skin darkening", "weight loss", "salt craving"]),
    ],
    "Nephrology": [
        ("Chronic_Kidney_Disease", ["fatigue", "swelling", "urinary changes", "back pain", "nausea"]),
        ("Kidney_Stones", ["severe back pain", "blood in urine", "nausea", "frequent urination", "fever"]),
        ("Glomerulonephritis", ["blood in urine", "swelling", "fatigue", "high blood pressure", "decreased urine"]),
        ("UTI", ["burning urination", "frequent urination", "blood in urine", "pelvic pain", "fever"]),
    ],
    "Rheumatology": [
        ("Lupus", ["fatigue", "joint pain", "rash", "fever", "photosensitivity"]),
        ("Fibromyalgia", ["widespread pain", "fatigue", "sleep problems", "mood issues", "cognitive difficulties"]),
        ("Gout", ["severe joint pain", "swelling", "redness", "heat in joint", "tophi"]),
        ("Psoriatic_Arthritis", ["joint pain", "skin lesions", "swelling", "stiffness", "nail changes"]),
        ("Vasculitis", ["fever", "fatigue", "weight loss", "skin rashes", "nerve problems"]),
    ],
}

# Drug mappings
DRUGS = {
    "Hypertension": ["Lisinopril", "Amlodipine", "Metoprolol", "Losartan"],
    "Arrhythmia": ["Amiodarone", "Diltiazem", "Sotalol"],
    "Coronary_Artery_Disease": ["Aspirin", "Atorvastatin", "Metoprolol", "Nitroglycerin"],
    "Heart_Failure": ["Furosemide", "Carvedilol", "Enalapril", "Spironolactone"],
    "Diabetes_Type_2": ["Metformin", "Glipizide", "Sitagliptin", "Empagliflozin"],
    "COPD": ["Albuterol", "Tiotropium", "Fluticasone", "Prednisone"],
    "Asthma": ["Albuterol", "Fluticasone", "Montelukast", "Budesonide"],
    "Pneumonia": ["Amoxicillin", "Azithromycin", "Levofloxacin"],
    "Lung_Cancer": ["Cisplatin", "Pembrolizumab", "Erlotinib"],
    "Migraine": ["Sumatriptan", "Propranolol", "Topiramate", "Amitriptyline"],
    "Epilepsy": ["Levetiracetam", "Carbamazepine", "Phenytoin", "Valproic_Acid"],
    "Osteoarthritis": ["Acetaminophen", "Ibuprofen", "Celecoxib", "Glucosamine"],
}


# ============================================================
# Patient Symptom Generator
# ============================================================

class PatientDataGenerator:
    """Generates synthetic patient symptom documents."""

    GENDERS = ["Male", "Female", "Other"]
    ADMISSION_REASONS = [
        "Emergency admission", "Scheduled admission", "Referral from clinic",
        "Follow-up treatment", "Diagnostic workup", "Surgical consultation"
    ]

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
        fake.seed_instance(seed)

    def generate_patients(self, count: int = 500) -> List[PatientSymptom]:
        """Generate a list of synthetic patient symptom documents."""
        patients = []
        diseases_list = self._get_diseases_by_field()
        departments = MEDICAL_FIELDS.copy()

        for i in range(count):
            # Pick a random disease and field
            field = random.choice(departments)
            diseases = diseases_list.get(field, [])
            if not diseases:
                field = random.choice(departments)
                diseases = diseases_list.get(field, [])
                if not diseases:
                    continue

            disease_name = random.choice(list(diseases.keys()))
            symptoms_list = diseases[disease_name]

            # Generate symptoms text
            chief_complaint = self._generate_chief_complaint(symptoms_list)
            full_symptoms = self._generate_full_symptoms(symptoms_list)
            history = self._generate_history(disease_name, symptoms_list)
            meds = self._generate_medications(disease_name)
            diagnosis = disease_name

            # Patient demographics
            age = random.randint(18, 85)
            gender = random.choice(self.GENDERS)

            # Admission date in last 2 years
            days_ago = random.randint(0, 730)
            admission_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

            severity = random.choices(
                [1, 2, 3, 4, 5],
                weights=[5, 15, 40, 25, 15]
            )[0]

            patient = PatientSymptom(
                patient_id=f"P{i+1:05d}",
                patient_id_int=i + 1,
                age=age,
                gender=gender,
                chief_complaint=chief_complaint,
                symptoms=full_symptoms,
                medical_history=history,
                current_medications=meds,
                initial_diagnosis=diagnosis,
                severity=severity,
                department=field,
                admission_date=admission_date,
            )
            patients.append(patient)

        return patients

    def _get_diseases_by_field(self) -> Dict[str, Dict[str, List[str]]]:
        diseases = {}
        for field, disease_list in DISEASES.items():
            if field not in diseases:
                diseases[field] = {}
            for disease_name, symptoms in disease_list:
                diseases[field][disease_name] = symptoms
        return diseases

    def _generate_chief_complaint(self, symptoms: List[str]) -> str:
        primary = random.choice(symptoms)
        duration = random.choice([
            "for 3 days", "for a week", "for 2 weeks", "since yesterday",
            "for several hours", "on and off for months", "recently developed"
        ])
        severity_desc = random.choice([
            "mild", "moderate", "severe", "persistent", "intermittent"
        ])
        return f"{primary.capitalize()} {duration}, described as {severity_desc}"

    def _generate_full_symptoms(self, symptoms: List[str]) -> str:
        n = random.randint(2, min(4, len(symptoms)))
        selected = random.sample(symptoms, n)
        descriptions = []
        for s in selected:
            duration = random.choice(["recently", "over the past week", "for several days", "chronic", "sudden onset"])
            desc = random.choice(["moderate", "mild", "severe", "persistent", "occasional"])
            descriptions.append(f"{s.capitalize()} ({desc}, {duration})")
        return "; ".join(descriptions)

    def _generate_history(self, disease: str, symptoms: List[str]) -> str:
        conditions = random.sample([
            "Type 2 Diabetes", "Hypertension", "Hypercholesterolemia",
            "Asthma", "GERD", "Anxiety", "Depression", "Hypothyroidism",
            "Obesity", "Previous surgery", "Allergic rhinitis"
        ], random.randint(1, 3))
        family_history = random.choice([
            "Family history: Father had Heart Disease",
            "Family history: Mother had Diabetes",
            "Family history: No significant family history",
            "Family history: Grandmother had Cancer",
        ])
        lifestyle = random.choice([
            "Non-smoker, occasional alcohol", "Smoker (10 pack-years)",
            "Non-smoker, regular exercise", "Smoker (20 pack-years), drinks alcohol regularly",
        ])
        return f"Past conditions: {', '.join(conditions)}. {family_history}. {lifestyle}."

    def _generate_medications(self, disease: str) -> str:
        if disease in DRUGS:
            meds = random.sample(DRUGS[disease], min(random.randint(1, 3), len(DRUGS[disease])))
            dosages = [f"{med} {random.choice(['10mg', '20mg', '50mg', '100mg'])} daily" for med in meds]
            return "; ".join(dosages) + ". Occasional acetaminophen for pain."
        return "Occasional acetaminophen for pain. No regular medications."

    def save_documents(self, patients: List[PatientSymptom], output_path: Path) -> None:
        """Save patients to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = [p.to_dict() for p in patients]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[DataGenerator] Saved {len(patients)} patient documents to {output_path}")


# ============================================================
# Graph Data Generator
# ============================================================

class GraphDataGenerator:
    """Generates synthetic disease correlation graph."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)

    def _edge_exists(self, edges: List[GraphEdge], n1: str, n2: str) -> bool:
        """Check if an edge already exists between two nodes."""
        for e in edges:
            if (e.source_id == n1 and e.target_id == n2) or \
               (e.source_id == n2 and e.target_id == n1):
                return True
        return False

    def generate_graph(self) -> tuple[List[GraphNode], List[GraphEdge]]:
        """Generate disease correlation graph nodes and edges."""
        nodes = []
        edges = []
        node_ids = set()

        # 1. Create medical field nodes
        field_nodes = {}
        for i, field in enumerate(MEDICAL_FIELDS):
            node_id = f"field_{field}"
            node = GraphNode(
                node_id=node_id,
                node_type=NodeType.MEDICAL_FIELD,
                label=field,
                properties={"description": f"Medical specialty: {field.replace('_', ' ')}"},
                degree=0
            )
            nodes.append(node)
            field_nodes[field] = node_id
            node_ids.add(node_id)

        # 2. Create disease nodes
        disease_nodes = {}
        disease_id_counter = 0
        for field, disease_list in DISEASES.items():
            for disease_name, _ in disease_list:
                node_id = f"disease_{disease_name}"
                if node_id in node_ids:
                    node_id = f"disease_{disease_name}_{disease_id_counter}"
                    disease_id_counter += 1
                disease_nodes[disease_name] = node_id
                node = GraphNode(
                    node_id=node_id,
                    node_type=NodeType.DISEASE,
                    label=disease_name,
                    properties={"medical_field": field},
                    degree=0
                )
                nodes.append(node)
                node_ids.add(node_id)

                # Connect disease to field
                edge = GraphEdge(
                    source_id=node_id,
                    target_id=field_nodes[field],
                    edge_type=EdgeType.DISEASE_TO_FIELD,
                    weight=0.5
                )
                edges.append(edge)
                edges.append(GraphEdge(
                    source_id=field_nodes[field],
                    target_id=node_id,
                    edge_type=EdgeType.DISEASE_TO_FIELD,
                    weight=0.5
                ))

        # 3. Create symptom nodes and connect to diseases
        symptom_nodes = {}
        all_symptoms = set()
        for field, disease_list in DISEASES.items():
            for disease_name, symptoms in disease_list:
                for symptom in symptoms:
                    all_symptoms.add(symptom.lower())

        for symptom in all_symptoms:
            node_id = f"symptom_{symptom.replace(' ', '_')}"
            symptom_nodes[symptom] = node_id
            node = GraphNode(
                node_id=node_id,
                node_type=NodeType.SYMPTOM,
                label=symptom,
                properties={"frequency": random.randint(1, 10)},
                degree=0
            )
            nodes.append(node)
            node_ids.add(node_id)

        # Connect symptoms to diseases
        for field, disease_list in DISEASES.items():
            for disease_name, symptoms in disease_list:
                disease_node_id = disease_nodes[disease_name]
                for symptom in symptoms:
                    symptom_node_id = symptom_nodes[symptom]
                    weight = round(random.uniform(0.3, 1.0), 2)
                    edges.append(GraphEdge(
                        source_id=disease_node_id,
                        target_id=symptom_node_id,
                        edge_type=EdgeType.DISEASE_TO_SYMPTOM,
                        weight=weight
                    ))
                    edges.append(GraphEdge(
                        source_id=symptom_node_id,
                        target_id=disease_node_id,
                        edge_type=EdgeType.DISEASE_TO_SYMPTOM,
                        weight=weight
                    ))

        # 4. Create drug nodes and connect to diseases
        drug_nodes = {}
        all_drugs = set()
        for drugs_list in DRUGS.values():
            for drug in drugs_list:
                all_drugs.add(drug)

        for drug in all_drugs:
            node_id = f"drug_{drug.replace(' ', '_')}"
            drug_nodes[drug] = node_id
            node = GraphNode(
                node_id=node_id,
                node_type=NodeType.DRUG,
                label=drug,
                properties={"category": "medication"},
                degree=0
            )
            nodes.append(node)
            node_ids.add(node_id)

        # Connect drugs to diseases
        for disease_name, drugs_list in DRUGS.items():
            if disease_name not in disease_nodes:
                continue
            disease_node_id = disease_nodes[disease_name]
            for drug in drugs_list:
                drug_node_id = drug_nodes[drug]
                edges.append(GraphEdge(
                    source_id=disease_node_id,
                    target_id=drug_node_id,
                    edge_type=EdgeType.DISEASE_TO_DRUG,
                    weight=0.7
                ))

        # 4b. Create intra-field disease edges (diseases sharing symptoms or in same field)
        field_to_diseases = {}
        for disease_name, disease_node_id in disease_nodes.items():
            for field, disease_list in DISEASES.items():
                if disease_name in [d[0] for d in disease_list]:
                    if field not in field_to_diseases:
                        field_to_diseases[field] = []
                    field_to_diseases[field].append((disease_name, disease_node_id))
                    break

        # For each field, add edges between diseases that share symptoms
        for field, diseases_in_field in field_to_diseases.items():
            disease_symptom_map = {}
            for disease_name, _ in diseases_in_field:
                disease_symptom_map[disease_name] = set()
                for d_name, symptoms in DISEASES.get(field, []):
                    if d_name == disease_name:
                        disease_symptom_map[disease_name] = set(symptoms)
                        break

            # Connect diseases that share at least 1 symptom
            for i, (d1, n1) in enumerate(diseases_in_field):
                for j, (d2, n2) in enumerate(diseases_in_field):
                    if i < j:
                        shared = disease_symptom_map.get(d1, set()) & disease_symptom_map.get(d2, set())
                        if shared:
                            # Higher weight for more shared symptoms
                            weight = round(0.3 + len(shared) * 0.15, 2)
                            weight = min(weight, 1.0)
                            edges.append(GraphEdge(
                                source_id=n1,
                                target_id=n2,
                                edge_type=EdgeType.DISEASE_TO_DISEASE,
                                weight=weight
                            ))

        # 5. Create additional inter-disease edges (comorbidities across fields)
        disease_names = list(disease_nodes.keys())
        for _ in range(50):
            d1 = random.choice(disease_names)
            d2 = random.choice(disease_names)
            if d1 != d2:
                n1 = disease_nodes[d1]
                n2 = disease_nodes[d2]
                # Check if already connected
                if not self._edge_exists(edges, n1, n2):
                    weight = round(random.uniform(0.1, 0.5), 2)
                    edges.append(GraphEdge(
                        source_id=n1,
                        target_id=n2,
                        edge_type=EdgeType.DISEASE_TO_DISEASE,
                        weight=weight
                    ))

        # 6. Create inter-symptom edges (related symptoms)
        symptom_names = list(symptom_nodes.keys())
        for _ in range(20):
            s1 = random.choice(symptom_names)
            s2 = random.choice(symptom_names)
            if s1 != s2:
                n1 = symptom_nodes[s1]
                n2 = symptom_nodes[s2]
                edges.append(GraphEdge(
                    source_id=n1,
                    target_id=n2,
                    edge_type=EdgeType.SYMPTOM_TO_SYMPTOM,
                    weight=round(random.uniform(0.1, 0.5), 2)
                ))

        # Calculate degrees
        node_degree = {}
        for edge in edges:
            node_degree[edge.source_id] = node_degree.get(edge.source_id, 0) + 1
            node_degree[edge.target_id] = node_degree.get(edge.target_id, 0) + 1

        for node in nodes:
            node.degree = node_degree.get(node.node_id, 0)

        print(f"[DataGenerator] Generated {len(nodes)} graph nodes and {len(edges)} edges")
        return nodes, edges

    def save_graph(self, nodes: List[GraphNode], edges: List[GraphEdge], output_path: Path) -> None:
        """Save graph data to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "nodes": [
                {
                    "node_id": n.node_id,
                    "node_type": n.node_type.value,
                    "label": n.label,
                    "properties": n.properties,
                    "degree": n.degree,
                }
                for n in nodes
            ],
            "edges": [
                {
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "edge_type": e.edge_type.value,
                    "weight": e.weight,
                }
                for e in edges
            ]
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[DataGenerator] Saved graph to {output_path}")


# ============================================================
# Main Data Generation Entry Point
# ============================================================

def generate_all_data():
    """Generate all synthetic medical data."""
    base_dir = Path(__file__).parent.parent.parent

    print("=" * 60)
    print("GENERATING MEDICAL KNOWLEDGE BASE DATA")
    print("=" * 60)

    # Generate patient documents
    print("\n[1/2] Generating Patient_Symptoms documents...")
    patient_gen = PatientDataGenerator(seed=42)
    patients = patient_gen.generate_patients(count=500)
    patient_path = base_dir / "data" / "raw" / "patient_symptoms.json"
    patient_gen.save_documents(patients, patient_path)

    # Generate disease graph
    print("\n[2/2] Generating Disease_Correlations graph...")
    graph_gen = GraphDataGenerator(seed=42)
    nodes, edges = graph_gen.generate_graph()
    graph_path = base_dir / "data" / "raw" / "disease_graph.json"
    graph_gen.save_graph(nodes, edges, graph_path)

    print("\n" + "=" * 60)
    print("DATA GENERATION COMPLETE")
    print(f"  - Patient documents: {len(patients)}")
    print(f"  - Graph nodes: {len(nodes)}")
    print(f"  - Graph edges: {len(edges)}")
    print("=" * 60)

    return patients, nodes, edges


if __name__ == "__main__":
    generate_all_data()
