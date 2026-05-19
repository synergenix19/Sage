# src/sage_poc/knowledge.py

KNOWLEDGE_DICT: dict[str, str] = {
    "what is anxiety": (
        "Anxiety is a normal stress response — feelings of worry, nervousness, or unease. "
        "When persistent and interfering with daily life, it may indicate an anxiety disorder. "
        "Evidence-based treatments include CBT, mindfulness, and sometimes medication."
    ),
    "what is depression": (
        "Depression is a mood disorder characterised by persistent low mood, loss of interest, "
        "and reduced energy. It affects how a person feels, thinks, and manages daily activities. "
        "CBT, DBT, and antidepressant medication are commonly effective treatments."
    ),
    "what is cbt": (
        "Cognitive Behavioral Therapy (CBT) is an evidence-based approach that helps identify "
        "and challenge unhelpful thought patterns and behaviours. It's structured, goal-oriented, "
        "and one of the most research-supported therapies for anxiety and depression."
    ),
    "what is dbt": (
        "Dialectical Behavior Therapy (DBT) combines CBT with mindfulness and acceptance strategies. "
        "It was developed for emotional dysregulation and is highly effective for managing "
        "intense emotions, interpersonal difficulties, and self-destructive behaviours."
    ),
    "what is mindfulness": (
        "Mindfulness is the practice of paying intentional, non-judgmental attention to the present moment. "
        "Research shows it reduces stress, anxiety, and depression. "
        "It can be practiced through breathing exercises, body scans, or everyday awareness."
    ),
    "what is burnout": (
        "Burnout is a state of chronic stress that leads to physical and emotional exhaustion, "
        "cynicism, and feelings of ineffectiveness. It's especially common in demanding work or caregiving roles. "
        "Recovery typically involves rest, boundary-setting, and addressing root stressors."
    ),
    "what is trauma": (
        "Trauma is an emotional response to a deeply distressing event. "
        "Effects can include flashbacks, avoidance, emotional numbness, and hypervigilance. "
        "Evidence-based treatments include EMDR and trauma-focused CBT."
    ),
    "what is self-care": (
        "Self-care refers to intentional practices that maintain and restore physical and emotional wellbeing. "
        "It includes sleep, nutrition, movement, social connection, and activities that restore energy. "
        "Effective self-care is personalised — what works varies between people."
    ),
    "what is stress": (
        "Stress is the body's response to perceived demands or threats. "
        "Short-term stress can be motivating; chronic stress harms physical and mental health. "
        "Management strategies include time management, relaxation techniques, and social support."
    ),
    "what is motivational interviewing": (
        "Motivational Interviewing (MI) is a person-centred counselling approach that explores ambivalence "
        "about change. It uses empathic listening, open questions, and affirmation to strengthen "
        "a person's own motivation and commitment to change."
    ),
}


def lookup_knowledge(query: str) -> str | None:
    query_lower = query.lower()
    for phrase, answer in KNOWLEDGE_DICT.items():
        if phrase in query_lower:
            return answer
    return None
