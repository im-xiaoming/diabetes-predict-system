from django.db import models

# Create your models here.
class Sex(models.TextChoices):
    MALE = 'male', 'Male'
    FEMALE = 'female', 'Female'
    
class Level(models.TextChoices):
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'
    VERY_HIGH = 'very_high', "Very high"

    
class Patient(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=50)
    age = models.PositiveIntegerField()
    sex = models.TextField(choices=Sex.choices)
    
    level = models.TextField(choices=Level.choices)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def war(self): # warning
        if self.level == 'low':
            return 0
        elif self.level == 'medium':
            return 1
        elif self.level == 'high':
            return 2
        return 3
    
    def __str__(self):
        return f'{self.id} - {self.name}'
    

class PatientTargetFeatures(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='patient_features')

    # 18. NEP - Nephropathy
    nep = models.BooleanField(
        default=False,
        verbose_name="Nephropathy"
    )

    # 19. NEU - Neuropathy
    neu = models.BooleanField(
        default=False,
        verbose_name="Neuropathy"
    )

    # 20. RET - Retinopathy
    ret = models.BooleanField(
        default=False,
        verbose_name="Retinopathy"
    )

    # 21. CV - Cardiovascular complication
    cv = models.BooleanField(
        default=False,
        verbose_name="Cardiovascular complication"
    )

    # 22. PER VAS - Peripheral Vascular complication
    per_vas = models.BooleanField(
        default=False,
        verbose_name="Peripheral Vascular complication"
    )
    
    def __str__(self):
        return f'{self.patient.id} - {self.patient.name} - {self.pk}'