from django.db import models
from django.db.models.signals import post_migrate
from django.dispatch import receiver

# Predefined classes list for initial population
PREDEFINED_CLASSES = [
    # Computer Science
    'CS 1301 - Intro to Computing',
    'CS 1331 - Intro to Object-Oriented Programming',
    'CS 1332 - Data Structures and Algorithms',
    'CS 2050 - Discrete Mathematics',
    'CS 2110 - Computer Organization and Programming',
    'CS 2340 - Objects and Design',
    'CS 3510 - Design and Analysis of Algorithms',
    'CS 3600 - Artificial Intelligence',
    'CS 4400 - Database Systems',
    'CS 4641 - Machine Learning',
    'CS 4650 - Natural Language Processing',
    
    # Mathematics
    'MATH 1551 - Differential Calculus',
    'MATH 1552 - Integral Calculus',
    'MATH 1553 - Linear Algebra',
    'MATH 1554 - Linear Algebra',
    'MATH 2550 - Multivariable Calculus',
    'MATH 2551 - Multivariable Calculus',
    'MATH 2552 - Differential Equations',
    'MATH 3012 - Applied Combinatorics',
    'MATH 3215 - Probability and Statistics',
    'MATH 3670 - Probability and Statistics',
    
    # Physics
    'PHYS 2211 - Intro Physics I',
    'PHYS 2212 - Intro Physics II',
    'PHYS 2213 - Modern Physics',
    
    # Chemistry
    'CHEM 1310 - General Chemistry',
    'CHEM 1311 - General Chemistry I',
    'CHEM 1312 - General Chemistry II',
    
    # Biology
    'BIOL 1510 - Biological Principles',
    'BIOL 1520 - Organismal Biology',
    
    # English/Writing
    'ENGL 1101 - English Composition I',
    'ENGL 1102 - English Composition II',
    'ENGL 2130 - American Literature',
    
    # History
    'HIST 2111 - US History to 1865',
    'HIST 2112 - US History Since 1865',
    
    # Economics
    'ECON 2100 - Principles of Economics',
    'ECON 2101 - Principles of Microeconomics',
    'ECON 2102 - Principles of Macroeconomics',
    
    # Psychology
    'PSYCH 1101 - Introduction to Psychology',
    'PSYCH 2015 - Research Methods',
    
    # Business
    'MGT 3000 - Principles of Management',
    'MGT 3062 - Financial Management',
    'ACCT 2101 - Principles of Accounting I',
    'ACCT 2102 - Principles of Accounting II',
    
    # Engineering (General)
    'ENG 1000 - Engineering Design',
    'ENG 1050 - Introduction to Engineering',
    
    # Other Common Core
    'PHIL 1010 - Introduction to Philosophy',
    'POL 1101 - American Government',
    'SOC 1101 - Introduction to Sociology',
    'STAT 2010 - Introduction to Statistics',
]


class Class(models.Model):
    name = models.CharField(max_length=200, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Class'
        verbose_name_plural = 'Classes'

    def __str__(self):
        return self.name


@receiver(post_migrate)
def create_default_classes(sender, **kwargs):
    """Automatically populate classes after running migrations"""
    if sender.name == 'classes':
        print("Creating default classes...")
        created_count = 0
        for class_name in PREDEFINED_CLASSES:
            cls, created = Class.objects.get_or_create(name=class_name)
            if created:
                created_count += 1
        print(f"Classes setup complete! Created {created_count} new classes.")