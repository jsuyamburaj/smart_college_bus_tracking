from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from .models import User, StudentProfile, DriverProfile, ParentProfile

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone', 'first_name', 'last_name',
                  'user_type', 'password', 'password2', 'profile_image', 
                  'is_verified', 'created_at', 'updated_at')
        read_only_fields = ('id', 'is_verified', 'created_at', 'updated_at')
        extra_kwargs = {
            'email': {'required': True},
            'phone': {'required': True},
        }
    
    def validate(self, attrs):
        # Check if passwords match
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        # Validate email format
        email = attrs.get('email')
        try:
            validate_email(email)
        except:
            raise serializers.ValidationError({"email": "Enter a valid email address."})
        
        # Check if user type is valid
        user_type = attrs.get('user_type')
        if user_type not in ['admin', 'driver', 'student', 'parent']:
            raise serializers.ValidationError({"user_type": "Invalid user type."})
        
        return attrs
    
    def create(self, validated_data):
        # Remove password2 from validated data
        validated_data.pop('password2')
        
        # Create user
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            phone=validated_data['phone'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            user_type=validated_data['user_type'],
            password=validated_data['password']
        )
        
        return user

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone', 'first_name', 'last_name',
                  'profile_image', 'user_type')
        read_only_fields = ('id', 'username', 'user_type')
        extra_kwargs = {
            'email': {'required': True},
            'phone': {'required': True},
        }
    
    def validate_email(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError({"email": "This email is already in use."})
        return value
    
    def validate_phone(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(phone=value).exists():
            raise serializers.ValidationError({"phone": "This phone number is already in use."})
        return value

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            # Try to authenticate with username or email
            user = authenticate(username=username, password=password)
            
            if not user:
                # Try with email
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
            
            if user:
                if not user.is_active:
                    raise serializers.ValidationError("User account is disabled.")
                
                attrs['user'] = user
                return attrs
            else:
                raise serializers.ValidationError("Unable to log in with provided credentials.")
        else:
            raise serializers.ValidationError("Must include 'username' and 'password'.")

class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentProfile
        fields = ('id', 'user', 'username', 'email', 'full_name', 'roll_number',
                  'department', 'year', 'semester', 'address', 'emergency_contact',
                  'assigned_bus', 'boarding_stop', 'qr_code')
        read_only_fields = ('id', 'user', 'username', 'email', 'full_name', 'qr_code')
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()
    
    def validate_roll_number(self, value):
        if self.instance:
            if StudentProfile.objects.exclude(pk=self.instance.pk).filter(roll_number=value).exists():
                raise serializers.ValidationError("This roll number is already in use.")
        else:
            if StudentProfile.objects.filter(roll_number=value).exists():
                raise serializers.ValidationError("This roll number is already in use.")
        return value

class StudentProfileCreateSerializer(serializers.ModelSerializer):
    user_data = UserSerializer(write_only=True)
    
    class Meta:
        model = StudentProfile
        fields = ('user_data', 'roll_number', 'department', 'year', 'semester',
                  'address', 'emergency_contact', 'assigned_bus', 'boarding_stop')
    
    def create(self, validated_data):
        user_data = validated_data.pop('user_data')
        user_data['user_type'] = 'student'  # Force student type
        
        # Create user
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        
        # Create student profile
        student_profile = StudentProfile.objects.create(user=user, **validated_data)
        return student_profile

class DriverProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = DriverProfile
        fields = ('id', 'user', 'username', 'email', 'full_name', 'license_number',
                  'experience', 'address', 'emergency_contact', 'assigned_bus',
                  'is_active', 'license_expiry')
        read_only_fields = ('id', 'user', 'username', 'email', 'full_name')
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()
    
    def validate_license_number(self, value):
        if self.instance:
            if DriverProfile.objects.exclude(pk=self.instance.pk).filter(license_number=value).exists():
                raise serializers.ValidationError("This license number is already in use.")
        else:
            if DriverProfile.objects.filter(license_number=value).exists():
                raise serializers.ValidationError("This license number is already in use.")
        return value

class DriverProfileCreateSerializer(serializers.ModelSerializer):
    user_data = UserSerializer(write_only=True)
    
    class Meta:
        model = DriverProfile
        fields = ('user_data', 'license_number', 'experience', 'address',
                  'emergency_contact', 'assigned_bus', 'is_active', 'license_expiry')
    
    def create(self, validated_data):
        user_data = validated_data.pop('user_data')
        user_data['user_type'] = 'driver'  # Force driver type
        
        # Create user
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        
        # Create driver profile
        driver_profile = DriverProfile.objects.create(user=user, **validated_data)
        return driver_profile

class ParentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    student_details = serializers.SerializerMethodField()
    
    class Meta:
        model = ParentProfile
        fields = ('id', 'user', 'student', 'student_details', 'relationship')
        read_only_fields = ('id', 'user', 'student_details')
    
    def get_student_details(self, obj):
        return {
            'id': obj.student.id,
            'roll_number': obj.student.roll_number,
            'name': obj.student.user.get_full_name(),
            'department': obj.student.department,
        }

class ParentProfileCreateSerializer(serializers.ModelSerializer):
    user_data = UserSerializer(write_only=True)
    
    class Meta:
        model = ParentProfile
        fields = ('user_data', 'student', 'relationship')
    
    def create(self, validated_data):
        user_data = validated_data.pop('user_data')
        user_data['user_type'] = 'parent'  # Force parent type
        
        # Create user
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        
        # Create parent profile
        parent_profile = ParentProfile.objects.create(user=user, **validated_data)
        return parent_profile

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)
    
    def validate(self, attrs):
        # Check if new passwords match
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"new_password": "New password fields didn't match."})
        
        # Check if old password is correct
        user = self.context['request'].user
        if not user.check_password(attrs['old_password']):
            raise serializers.ValidationError({"old_password": "Old password is not correct."})
        
        return attrs

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user found with this email address.")
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    uid = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs

class UserListSerializer(serializers.ModelSerializer):
    profile_type = serializers.SerializerMethodField()
    profile_details = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone', 'first_name', 'last_name',
                  'user_type', 'profile_type', 'profile_details', 'is_active',
                  'is_verified', 'created_at')
    
    def get_profile_type(self, obj):
        if obj.user_type == 'student':
            return 'Student'
        elif obj.user_type == 'driver':
            return 'Driver'
        elif obj.user_type == 'parent':
            return 'Parent'
        elif obj.user_type == 'admin':
            return 'Admin'
        return 'Unknown'
    
    def get_profile_details(self, obj):
        try:
            if obj.user_type == 'student':
                profile = obj.student_profile
                return {
                    'roll_number': profile.roll_number,
                    'department': profile.department,
                    'year': profile.year,
                    'assigned_bus': profile.assigned_bus.bus_number if profile.assigned_bus else None,
                }
            elif obj.user_type == 'driver':
                profile = obj.driver_profile
                return {
                    'license_number': profile.license_number,
                    'experience': profile.experience,
                    'assigned_bus': profile.assigned_bus.bus_number if profile.assigned_bus else None,
                }
            elif obj.user_type == 'parent':
                profile = obj.parent_profile
                return {
                    'student_name': profile.student.user.get_full_name(),
                    'relationship': profile.relationship,
                }
        except:
            pass
        return {}