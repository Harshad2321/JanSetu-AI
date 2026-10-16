"""
JanSetu AI — Synthetic Multilingual Civic Complaint Dataset Generator (Phase 4).

Generates reproducible, clearly labelled synthetic civic complaint data for:
- pothole
- waterlogging
- garbage

Languages covered:
- English (en)
- Hindi (hi)
- Marathi (mr)
- Hinglish (hinglish)

All generated records are strictly synthetic (is_synthetic=True) for educational/PoC use.
A distinct challenge set is generated with disjoint phrasing patterns to evaluate generalization
without leakage.
"""

from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path
from typing import Any, Dict, List, Tuple

VALID_CATEGORIES: List[str] = ["pothole", "waterlogging", "garbage"]
VALID_LANGUAGES: List[str] = ["en", "hi", "mr", "hinglish"]

# Canonical Seed
DEFAULT_RANDOM_SEED: int = 42


def _build_training_templates() -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """
    Returns diverse, structured templates for training data across all categories and languages.
    Covers formal/informal styles, duration, location, safety clues, and code-switching.
    """
    return {
        "pothole": {
            "en": [
                {
                    "text": "Deep dangerous pothole on {location} causing two-wheelers to skid and lose balance for the past {duration}.",
                    "formality": "informal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "Formal complaint regarding extensive crater-like road depression near {location}. Multiple vehicles damaged over {duration}.",
                    "formality": "formal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "Huge pothole right in the middle of {location}. Needs urgent asphalt patch repair.",
                    "formality": "informal",
                    "has_safety_clue": False,
                    "has_location_reference": True,
                },
                {
                    "text": "Deep trench and road cavity across {location} causing severe vehicular hazard.",
                    "formality": "formal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "The road surface near {location} has completely broken down with several sharp potholes.",
                    "formality": "formal",
                    "has_safety_clue": False,
                    "has_location_reference": True,
                },
                {
                    "text": "Severe road cavity opposite {location}. An elderly pedestrian tripped yesterday.",
                    "formality": "formal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "Massive pothole opened up after yesterday's rain on {location}. Traffic is completely choked.",
                    "formality": "informal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
            ],
            "hi": [
                {
                    "text": "{location} पर बहुत बड़ा और गहरा गड्ढा है, पिछले {duration} से बाइक सवार गिर रहे हैं।",
                    "formality": "informal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "{location} के मुख्य मार्ग पर सड़क टूट गई है और खतरनाक गड्ढे बन गए हैं। कृपया डामरीकरण कराएं।",
                    "formality": "formal",
                    "has_safety_clue": False,
                    "has_location_reference": True,
                },
                {
                    "text": "{location} के सामने सड़क का गड्डा जानलेवा साबित हो रहा है, तुरंत मरम्मत की आवश्यकता है।",
                    "formality": "formal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "सड़क पर गड्ढे की वजह से {location} के पास आए दिन गाड़ियां दुर्घटनाग्रस्त हो रही हैं।",
                    "formality": "informal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "{location} के पास सड़क धंस गई है और भारी गड्डा बन गया है।",
                    "formality": "informal",
                    "has_safety_clue": False,
                    "has_location_reference": True,
                },
            ],
            "mr": [
                {
                    "text": "{location} येथे रस्त्यावर प्रचंड मोठा खड्डा पडला असून दुचाकीस्वार घसरून पडत आहेत.",
                    "formality": "informal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "{location} परिसरातील मुख्य रस्त्यावर मोठे खड्डे पडले असून {duration} पासून वाहनचालकांचे हाल होत आहेत.",
                    "formality": "formal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "{location} जवळ रस्त्याची चाळण झाली आहे, खड्ड्यांमुळे गंभीर अपघाताची शक्यता आहे.",
                    "formality": "informal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "रस्त्यावरील खड्डा त्वरित बुजवण्यात यावा, {location} समोरील रस्ता खचला आहे.",
                    "formality": "formal",
                    "has_safety_clue": False,
                    "has_location_reference": True,
                },
            ],
            "hinglish": [
                {
                    "text": "{location} pe bohot bada pothole hai, {duration} se log gir rahe hain bike se.",
                    "formality": "informal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "Dangerous gadha near {location}. Tyre burst ho gaya ek car ka kal raat ko.",
                    "formality": "informal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "{location} main road pe deep crater ban gaya hai, BMC please patch work karvao urgently.",
                    "formality": "formal",
                    "has_safety_clue": False,
                    "has_location_reference": True,
                },
                {
                    "text": "Bohot bada road pothole hai outside {location}, traffic slow ho raha hai and risk hai.",
                    "formality": "informal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
            ],
        },
        "waterlogging": {
            "en": [
                {
                    "text": "Severe waterlogging on {location} with knee-deep stagnant water standing for {duration}.",
                    "formality": "formal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "Stormwater drain blocked near {location}, rainwater flooding into roadside shops and houses.",
                    "formality": "formal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "Road submerged in dirty water outside {location}. Pedestrians unable to cross.",
                    "formality": "informal",
                    "has_safety_clue": False,
                    "has_location_reference": True,
                },
                {
                    "text": "Heavy water accumulation near {location} creating mosquito breeding ground for {duration}.",
                    "formality": "formal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "Submerged road and overflowing nullah causing severe water logging near {location}.",
                    "formality": "informal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
            ],
            "hi": [
                {
                    "text": "{location} पर भारी जलभराव हो गया है, घुटनों तक गंदा पानी {duration} से भरा हुआ है।",
                    "formality": "formal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "{location} के पास नाला चोक होने से बारिश का पानी सड़कों और घरों में घुस रहा है।",
                    "formality": "formal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "सड़क पर पानी भरा हुआ है {location} के सामने, गाड़ियां बंद पड़ रही हैं।",
                    "formality": "informal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "{location} पर जलजमाव की समस्या बहुत गंभीर है, नाले की सफाई तुरंत करवाएं।",
                    "formality": "formal",
                    "has_safety_clue": False,
                    "has_location_reference": True,
                },
            ],
            "mr": [
                {
                    "text": "{location} येथे रस्त्यावर प्रचंड पाणी साचले असून गुडघाभर पाण्यातून वाट काढावी लागत आहे.",
                    "formality": "informal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "{location} परिसरातील गटार तुंबल्यामुळे पावसाचे पाणी रस्त्यावर पसरले आहे.",
                    "formality": "formal",
                    "has_safety_clue": False,
                    "has_location_reference": True,
                },
                {
                    "text": "पाणी साचल्यामुळे {location} समोरील वाहतूक पूर्णपणे ठप्प झाली आहे, {duration} झाले पाणी ओसरत नाही.",
                    "formality": "formal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "{location} जवळ सांडपाणी रस्त्यावर आल्यामुळे साथीचे आजार पसरण्याची भीती आहे.",
                    "formality": "formal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
            ],
            "hinglish": [
                {
                    "text": "{location} pe knee deep waterlogging ho gayi hai, cars and bikes breakdown ho rahe hain.",
                    "formality": "informal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "Drain block hone ki wajah se poora paani bhara hua hai near {location} since {duration}.",
                    "formality": "informal",
                    "has_safety_clue": False,
                    "has_location_reference": True,
                },
                {
                    "text": "Severe water accumulation outside {location}, dirty paani road pe jama hai please drain out.",
                    "formality": "formal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "Gutter overflow ho raha hai and waterlogging at {location}, walk karna impossible hai.",
                    "formality": "informal",
                    "has_safety_clue": False,
                    "has_location_reference": True,
                },
            ],
        },
        "garbage": {
            "en": [
                {
                    "text": "Huge heap of uncollected solid waste and rotting garbage dumped outside {location} for {duration}.",
                    "formality": "formal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "Overflowing public trash dump near {location}. Stray cattle and dogs scattering refuse on road.",
                    "formality": "informal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "Severe stench from municipal garbage mound opposite {location}. Posing severe health hazard.",
                    "formality": "formal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "Garbage bin not cleared for {duration} near {location}. Waste spilling over onto pedestrian walkway.",
                    "formality": "formal",
                    "has_safety_clue": False,
                    "has_location_reference": True,
                },
                {
                    "text": "Illegal dumping of vegetable and plastic waste behind {location}. Urgent clearance needed.",
                    "formality": "informal",
                    "has_safety_clue": False,
                    "has_location_reference": True,
                },
            ],
            "hi": [
                {
                    "text": "{location} के पास कचरे का भारी ढेर लगा हुआ है, पिछले {duration} से कोई सफाई नहीं हुई।",
                    "formality": "informal",
                    "has_safety_clue": False,
                    "has_location_reference": True,
                },
                {
                    "text": "{location} पर सड़े हुए कूड़े की दुर्गंध से सांस लेना मुश्किल हो गया है, बीमारी फैलने का खतरा है।",
                    "formality": "formal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "कचरा पेटी ओवरफ्लो हो रही है {location} के सामने, आवारा पशु कूड़ा सड़क पर फैला रहे हैं।",
                    "formality": "informal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "{location} में सार्वजनिक स्थल पर अवैध रूप से कूड़ा डंप किया गया है। तुरंत उठवाएं।",
                    "formality": "formal",
                    "has_safety_clue": False,
                    "has_location_reference": True,
                },
            ],
            "mr": [
                {
                    "text": "{location} येथे कचऱ्याचे प्रचंड साम्राज्य पसरले असून {duration} पासून कचरा उचललेला नाही.",
                    "formality": "informal",
                    "has_safety_clue": False,
                    "has_location_reference": True,
                },
                {
                    "text": "{location} परिसरातील कचराकुंडी तुडुंब भरून वाहत आहे, दुर्गंधीमुळे नागरिकांचे आरोग्य धोक्यात आले आहे.",
                    "formality": "formal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "रस्त्याकडेला साचलेल्या कचऱ्यामुळे {location} येथे डासांचा प्रादुर्भाव वाढला आहे, त्वरित स्वच्छता करा.",
                    "formality": "formal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "{location} जवळ घाणीचे साम्राज्य निर्माण झाले असून घंटागाडी वेळेवर येत नाही.",
                    "formality": "informal",
                    "has_safety_clue": False,
                    "has_location_reference": True,
                },
            ],
            "hinglish": [
                {
                    "text": "Bohot sara kachra dumped outside {location}, badbu aa rahi hai since {duration}.",
                    "formality": "informal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "Dustbin overflow ho gaya hai at {location}, garbage road pe faila hua hai please pick up.",
                    "formality": "informal",
                    "has_safety_clue": False,
                    "has_location_reference": True,
                },
                {
                    "text": "Uncollected solid waste pile near {location}, health risk hai colony residents ke liye.",
                    "formality": "formal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
                {
                    "text": "Kachra vehicle nahi aaya {duration} se near {location}, rotten waste spilling everywhere.",
                    "formality": "informal",
                    "has_safety_clue": True,
                    "has_location_reference": True,
                },
            ],
        },
    }


def _build_challenge_examples() -> List[Dict[str, Any]]:
    """
    Returns distinctly phrased, realistic challenge complaints across categories and languages.
    Uses vocabulary, idiomatic expressions, bureaucratic phrasing, and complex code-switching
    that do NOT overlap with training templates, preventing test-train data leakage.
    """
    return [
        # Pothole challenge complaints
        {
            "id": "chal_pothole_01",
            "text": "The carriageway bitumen has disintegrated into a moon crater; an autorickshaw toppled sideways this morning near the flyover pillar.",
            "label": "pothole",
            "language": "en",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_pothole_02",
            "text": "Tar layer peeled off exposing sharp rubble aggregates; scooters skidding during morning rush hours outside the metro station.",
            "label": "pothole",
            "language": "en",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_pothole_03",
            "text": "फ्लाईओवर के उतरते ही डामर उखड़ चुका है और धातु की गिट्टियां बिखरने से दोपहिया का संतुलन बिगड़ रहा है।",
            "label": "pothole",
            "language": "hi",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_pothole_04",
            "text": "रस्त्यावरील डांबर पूर्णपणे निघून गेले असून लोखंडी गज आणि खडी बाहेर आल्याने वाहनांचे टायर फुटत आहेत.",
            "label": "pothole",
            "language": "mr",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_pothole_05",
            "text": "Road ka surface ekdum cratered ho chuka hai, sharp stones exposed hain jisse balance bigad raha hai.",
            "label": "pothole",
            "language": "hinglish",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_pothole_06",
            "text": "Depression on south carriageway forming dangerous wheel-trap for cyclers and delivery agents.",
            "label": "pothole",
            "language": "en",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_pothole_07",
            "text": "गाड़ी का चेसिस नीचे टकरा गया इतना भयानक गर्त बना हुआ है सड़क के बीचों-बीच।",
            "label": "pothole",
            "language": "hi",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_pothole_08",
            "text": "वाहनाचा एक्सल तुटण्याची वेळ आली आहे इतका खोल खड्डा पुलाच्या पायथ्याशी निर्माण झालाय.",
            "label": "pothole",
            "language": "mr",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_pothole_09",
            "text": "Suspension damage ho gaya scooty ka because bitumen layer sink ho gayi hai under heavy axle load.",
            "label": "pothole",
            "language": "hinglish",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_pothole_10",
            "text": "Unsurfaced trench left unpaved after utility pipe excavation posing severe collision hazard.",
            "label": "pothole",
            "language": "en",
            "is_synthetic": True,
            "partition": "challenge",
        },

        # Waterlogging challenge complaints
        {
            "id": "chal_water_01",
            "text": "Subway underpass completely inundated up to waist height, marooning commuter buses in brown sludge.",
            "label": "waterlogging",
            "language": "en",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_water_02",
            "text": "Monsoon culvert backflow submerged the ground floor staircases; electrical meters submerged.",
            "label": "waterlogging",
            "language": "en",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_water_03",
            "text": "अंडरपास में नाले का गंदा पानी भर गया है, बिजली के पोल तक पानी पहुंचने से करंट का अंदेशा है।",
            "label": "waterlogging",
            "language": "hi",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_water_04",
            "text": "रेल्वे भुयारी मार्गात सांडपाण्याचा फुगवटा निर्माण झाला असून संपूर्ण वाहतूक ठप्प पडली आहे.",
            "label": "waterlogging",
            "language": "mr",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_water_05",
            "text": "Underpass submerged ho chuka hai dirty gutter runoff se, electric feeder box paani mein doob raha hai.",
            "label": "waterlogging",
            "language": "hinglish",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_water_06",
            "text": "Backflow in stormwater outlet drowning the entire access alleyway under contaminated urban runoff.",
            "label": "waterlogging",
            "language": "en",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_water_07",
            "text": "गली में जमा दूषित जलस्तर कम नहीं हो रहा, बच्चों का स्कूल जाना असंभव हो गया है।",
            "label": "waterlogging",
            "language": "hi",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_water_08",
            "text": "पाण्याचा निचरा करणारी वाहिनी तुटल्यामुळे चिखल आणि मैला रस्त्यावर साचून तळे साचले आहे.",
            "label": "waterlogging",
            "language": "mr",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_water_09",
            "text": "Sludge water drain nahi ho raha hai street se, stinking dirty pond ban chuka hai society ke entrance pe.",
            "label": "waterlogging",
            "language": "hinglish",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_water_10",
            "text": "Retention basin overwhelmed; stagnant brackish water blocking civic hospital access ramp.",
            "label": "waterlogging",
            "language": "en",
            "is_synthetic": True,
            "partition": "challenge",
        },

        # Garbage challenge complaints
        {
            "id": "chal_garbage_01",
            "text": "Rancid bio-waste and commercial poultry remnants decaying in open view, producing nauseating fumes.",
            "label": "garbage",
            "language": "en",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_garbage_02",
            "text": "Unauthorized dumping site emitting putrid methane odors; swarms of flies encroaching primary school.",
            "label": "garbage",
            "language": "en",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_garbage_03",
            "text": "अस्पताल के निकट मेडिकल अवशेष और सड़ा हुआ गीला कचरा खुला पड़ा है, तीव्र बदबू से जीना दूभर है।",
            "label": "garbage",
            "language": "hi",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_garbage_04",
            "text": "उघड्यावर टाकलेल्या कुजक्या कचऱ्यामुळे माशांचा सुळसुळाट झाला असून तीव्र दुर्गंधीने श्वास घेणे अशक्य झाले आहे.",
            "label": "garbage",
            "language": "mr",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_garbage_05",
            "text": "Open space pe decomposing organic waste dump kar diya hai, intolerable foul smell and flies infestation.",
            "label": "garbage",
            "language": "hinglish",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_garbage_06",
            "text": "Municipal skip bin fractured and overflowing with fermenting refuse blocking pedestrian walkway.",
            "label": "garbage",
            "language": "en",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_garbage_07",
            "text": "बाजार का सड़ा-गला जैविक कचरा खुले मैदान में फेंका जा रहा है, आवारा कुत्ते आतंक मचा रहे हैं।",
            "label": "garbage",
            "language": "hi",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_garbage_08",
            "text": "कचरा संकलन केंद्र बंद असल्याने नागरीकांनी रस्त्यावरच कचऱ्याचे ढीग केले आहेत, त्वरित उचलण्यात यावेत.",
            "label": "garbage",
            "language": "mr",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_garbage_09",
            "text": "Plastic waste and wet rotting dump road edge pe block kar raha hai, sanitary inspection team bhejye.",
            "label": "garbage",
            "language": "hinglish",
            "is_synthetic": True,
            "partition": "challenge",
        },
        {
            "id": "chal_garbage_10",
            "text": "Pungent heaps of uncleared household debris creating breeding ground for rodents near maternity ward.",
            "label": "garbage",
            "language": "en",
            "is_synthetic": True,
            "partition": "challenge",
        },
    ]


LOCATIONS: List[str] = [
    "Dadar West Station Road",
    "SV Road near Andheri subway",
    "LBS Marg Kurla",
    "MG Road junction",
    "Sector 17 Vashi market",
    "Link Road Malad",
    "FC Road Deccan",
    "JM Road near bus stop",
    "Nehru Chowk opposite bank",
    "Station Road near vegetable market",
    "Shivaji Nagar 4th cross",
    "Gandhi Circle main avenue",
]

DURATIONS: List[str] = [
    "3 days",
    "48 hours",
    "one week",
    "last 4 days",
    "yesterday",
    "past 5 days",
    "almost two weeks",
]


def generate_synthetic_datasets(
    seed: int = DEFAULT_RANDOM_SEED,
    samples_per_category: int = 100,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Generates deterministic synthetic training and challenge datasets.
    
    Returns:
    - (training_examples, challenge_examples)
    """
    rng = random.Random(seed)
    templates = _build_training_templates()
    train_records: List[Dict[str, Any]] = []

    record_counter = 1
    for category in VALID_CATEGORIES:
        cat_templates = templates[category]
        generated_for_cat = 0

        while generated_for_cat < samples_per_category:
            for lang in VALID_LANGUAGES:
                lang_pool = cat_templates.get(lang, [])
                if not lang_pool:
                    continue

                tmpl = rng.choice(lang_pool)
                loc = rng.choice(LOCATIONS)
                dur = rng.choice(DURATIONS)

                text = tmpl["text"].format(location=loc, duration=dur)

                train_records.append({
                    "id": f"syn_{record_counter:04d}",
                    "text": text,
                    "label": category,
                    "language": lang,
                    "formality": tmpl.get("formality", "informal"),
                    "has_safety_clue": tmpl.get("has_safety_clue", False),
                    "has_location_reference": tmpl.get("has_location_reference", True),
                    "is_synthetic": True,
                    "partition": "train",
                })
                record_counter += 1
                generated_for_cat += 1
                if generated_for_cat >= samples_per_category:
                    break

    # Shuffle training records with fixed seed
    rng.shuffle(train_records)

    # Distinct challenge set
    challenge_records = _build_challenge_examples()

    return train_records, challenge_records


def save_datasets(
    train_data: List[Dict[str, Any]],
    challenge_data: List[Dict[str, Any]],
    output_dir: Path,
) -> Tuple[Path, Path]:
    """Saves generated datasets to target directory in JSON format."""
    output_dir.mkdir(parents=True, exist_ok=True)
    train_path = output_dir / "synthetic_complaints_train.json"
    challenge_path = output_dir / "synthetic_complaints_challenge.json"

    with open(train_path, "w", encoding="utf-8") as f:
        json.dump(train_data, f, indent=2, ensure_ascii=False)

    with open(challenge_path, "w", encoding="utf-8") as f:
        json.dump(challenge_data, f, indent=2, ensure_ascii=False)

    return train_path, challenge_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic multilingual civic complaint datasets.")
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED, help="Random seed for deterministic generation")
    parser.add_argument("--samples-per-cat", type=int, default=100, help="Samples per category in training split")
    parser.add_argument("--output-dir", type=str, default="data", help="Output directory relative to workspace root")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    out_dir = repo_root / args.output_dir

    print(f"Generating synthetic datasets (seed={args.seed}, samples_per_cat={args.samples_per_cat})...")
    train_records, challenge_records = generate_synthetic_datasets(
        seed=args.seed,
        samples_per_category=args.samples_per_cat,
    )

    train_file, chal_file = save_datasets(train_records, challenge_records, out_dir)
    print(f"[SUCCESS] Saved {len(train_records)} training records to: {train_file}")
    print(f"[SUCCESS] Saved {len(challenge_records)} challenge records to: {chal_file}")

    # Summary statistics
    by_cat = {}
    by_lang = {}
    for r in train_records:
        by_cat[r["label"]] = by_cat.get(r["label"], 0) + 1
        by_lang[r["language"]] = by_lang.get(r["language"], 0) + 1

    print(f"Training distribution by category: {by_cat}")
    print(f"Training distribution by language: {by_lang}")


if __name__ == "__main__":
    main()
