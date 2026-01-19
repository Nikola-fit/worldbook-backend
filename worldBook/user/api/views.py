from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .serializers import UserSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def registration_view(request):
    serializer = UserSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()
        return Response(
            {
                "message": "User was registered successfully",
                "username": user.username,  # Fix this to match AbstractUser field
                "email": user.email,
            },
            status=201,
        )
    return Response(serializer.errors, status=400)
