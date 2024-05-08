"""
This Python file is part of a FastAPI application, demonstrating user management functionalities including creating, reading,
updating, and deleting (CRUD) user information. It uses OAuth2 with Password Flow for security, ensuring that only authenticated
users can perform certain operations. Additionally, the file showcases the integration of FastAPI with SQLAlchemy for asynchronous
database operations, enhancing performance by non-blocking database calls.

The implementation emphasizes RESTful API principles, with endpoints for each CRUD operation and the use of HTTP status codes
and exceptions to communicate the outcome of operations. It introduces the concept of HATEOAS (Hypermedia as the Engine of
Application State) by including navigational links in API responses, allowing clients to discover other related operations dynamically.

OAuth2PasswordBearer is employed to extract the token from the Authorization header and verify the user's identity, providing a layer
of security to the operations that manipulate user data.

Key Highlights:
- Use of FastAPI's Dependency Injection system to manage database sessions and user authentication.
- Demonstrates how to perform CRUD operations in an asynchronous manner using SQLAlchemy with FastAPI.
- Implements HATEOAS by generating dynamic links for user-related actions, enhancing API discoverability.
- Utilizes OAuth2PasswordBearer for securing API endpoints, requiring valid access tokens for operations.
"""

from builtins import dict, int, len, str
from datetime import timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_current_user, get_db, get_email_service, require_role
from app.schemas.pagination_schema import EnhancedPagination
from app.schemas.token_schema import TokenResponse
from app.schemas.user_schemas import LoginRequest, UserBase, UserCreate, UserListResponse, UserResponse, UserUpdate
from app.services.user_service import *
from app.services.jwt_service import create_access_token
from app.utils.link_generation import create_user_links, generate_pagination_links
from app.dependencies import get_settings
from app.services.email_service import EmailService
# 
from fastapi.responses import HTMLResponse
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

# 

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
settings = get_settings()
from app.models.user_model import User

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user_model import User  # Import the User model
from app.services.user_service import UserService
from app.schemas.user_schemas import UserCreate, UserUpdate
from app.dependencies import get_db

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.user_service import UserService
from app.models.user_model import User

router = APIRouter()


@router.get("/loginpage/", response_class=FileResponse, tags=["Login and Registration"])
async def get_login_page():
    # Endpoint to serve the LOGIN PAGE
    return "app/templates/login.html"

@router.get("/", response_class=FileResponse, tags=["Login and Registration"])
async def get_register_page():
    # Endpoint to serve the REGISTER PAGE
    return "app/templates/register.html"

@router.get("/profile/{user_id}", response_class=FileResponse, tags=["User Profile"])
async def get_user_profile_page(request: Request, user_id: str):
    # Fetch user data from the database based on user_id
    return "app/templates/index.html"

@router.get("/users/{user_id}", response_model=UserResponse, name="get_user", tags=["User Management Requires (Admin or Manager Roles)"])
async def get_user(user_id: UUID, request: Request, db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme), current_user: dict = Depends(require_role(["ADMIN", "MANAGER"]))):
    """
    Endpoint to fetch a user by their unique identifier (UUID).

    Utilizes the UserService to query the database asynchronously for the user and constructs a response
    model that includes the user's details along with HATEOAS links for possible next actions.

    Args:
        user_id: UUID of the user to fetch.
        request: The request object, used to generate full URLs in the response.
        db: Dependency that provides an AsyncSession for database access.
        token: The OAuth2 access token obtained through OAuth2PasswordBearer dependency.
    """
    user = await UserService.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserResponse.model_construct(
        id=user.id,
        nickname=user.nickname,
        first_name=user.first_name,
        last_name=user.last_name,
        bio=user.bio,
        profile_picture_url=user.profile_picture_url,
        github_profile_url=user.github_profile_url,
        linkedin_profile_url=user.linkedin_profile_url,
        role=user.role,
        email=user.email,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        links=create_user_links(user.id, request)  
    )

# Additional endpoints for update, delete, create, and list users follow a similar pattern, using
# asynchronous database operations, handling security with OAuth2PasswordBearer, and enhancing response
# models with dynamic HATEOAS links.

# This approach not only ensures that the API is secure and efficient but also promotes a better client
# experience by adhering to REST principles and providing self-discoverable operations.

@router.put("/users/{user_id}", response_model=UserResponse, name="update_user", tags=["User Management Requires (Admin or Manager Roles)"])
async def update_user(user_id: UUID, user_update: UserUpdate, request: Request, db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme), current_user: dict = Depends(require_role(["ADMIN", "MANAGER"]))):
    """
    Update user information.

    - **user_id**: UUID of the user to update.
    - **user_update**: UserUpdate model with updated user information.
    """
    user_data = user_update.model_dump(exclude_unset=True)
    updated_user = await UserService.update(db, user_id, user_data)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserResponse.model_construct(
        id=updated_user.id,
        bio=updated_user.bio,
        first_name=updated_user.first_name,
        last_name=updated_user.last_name,
        nickname=updated_user.nickname,
        email=updated_user.email,
        role=updated_user.role,
        last_login_at=updated_user.last_login_at,
        profile_picture_url=updated_user.profile_picture_url,
        github_profile_url=updated_user.github_profile_url,
        linkedin_profile_url=updated_user.linkedin_profile_url,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at,
        links=create_user_links(updated_user.id, request)
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, name="delete_user", tags=["User Management Requires (Admin or Manager Roles)"])
async def delete_user(user_id: UUID, db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme), current_user: dict = Depends(require_role(["ADMIN", "MANAGER"]))):
    """
    Delete a user by their ID.

    - **user_id**: UUID of the user to delete.
    """
    success = await UserService.delete(db, user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)



@router.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["User Management Requires (Admin or Manager Roles)"], name="create_user")
async def create_user(user: UserCreate, request: Request, db: AsyncSession = Depends(get_db), email_service: EmailService = Depends(get_email_service), token: str = Depends(oauth2_scheme), current_user: dict = Depends(require_role(["ADMIN", "MANAGER"]))):
    """
    Create a new user.

    This endpoint creates a new user with the provided information. If the email
    already exists, it returns a 400 error. On successful creation, it returns the
    newly created user's information along with links to related actions.

    Parameters:
    - user (UserCreate): The user information to create.
    - request (Request): The request object.
    - db (AsyncSession): The database session.

    Returns:
    - UserResponse: The newly created user's information along with navigation links.
    """
    existing_user = await UserService.get_by_email(db, user.email)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
    
    created_user = await UserService.create(db, user.model_dump(), email_service)
    if not created_user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user")
    
    
    return UserResponse.model_construct(
        id=created_user.id,
        bio=created_user.bio,
        first_name=created_user.first_name,
        last_name=created_user.last_name,
        profile_picture_url=created_user.profile_picture_url,
        nickname=created_user.nickname,
        email=created_user.email,
        role=created_user.role,
        last_login_at=created_user.last_login_at,
        created_at=created_user.created_at,
        updated_at=created_user.updated_at,
        links=create_user_links(created_user.id, request)
    )


@router.get("/users/", response_model=UserListResponse, tags=["User Management Requires (Admin or Manager Roles)"])
async def list_users(
    request: Request,
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role(["ADMIN", "MANAGER"]))
):
    total_users = await UserService.count(db)
    users = await UserService.list_users(db, skip, limit)

    user_responses = [
        UserResponse.model_validate(user) for user in users
    ]
    
    pagination_links = generate_pagination_links(request, skip, limit, total_users)
    
    # Construct the final response with pagination details
    return UserListResponse(
        items=user_responses,
        total=total_users,
        page=skip // limit + 1,
        size=len(user_responses),
        links=pagination_links  # Ensure you have appropriate logic to create these links
    )


@router.post("/register/", response_model=UserResponse, tags=["Login and Registration"])
async def register(user_data: UserCreate, session: AsyncSession = Depends(get_db), email_service: EmailService = Depends(get_email_service)):
    user = await UserService.register_user(session, user_data.model_dump(), email_service)
    if user:
        return user
    raise HTTPException(status_code=400, detail="Email already exists")

@router.post("/login/", response_model=TokenResponse, tags=["Login and Registration"])
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_db)):
    if await UserService.is_account_locked(session, form_data.username):
        raise HTTPException(status_code=400, detail="Account locked due to too many failed login attempts.")

    user = await UserService.login_user(session, form_data.username, form_data.password)
    if user:
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)

        access_token = create_access_token(
            data={"sub": user.email, "role": str(user.role.name)},
            expires_delta=access_token_expires
        )

        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Incorrect email or password.")

@router.post("/login/", include_in_schema=False, response_model=TokenResponse, tags=["Login and Registration"])
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_db)):
    if await UserService.is_account_locked(session, form_data.username):
        raise HTTPException(status_code=400, detail="Account locked due to too many failed login attempts.")

    user = await UserService.login_user(session, form_data.username, form_data.password)
    if user:
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)

        access_token = create_access_token(
            data={"sub": user.email, "role": str(user.role.name)},
            expires_delta=access_token_expires
        )

        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Incorrect email or password.")


@router.get("/verify-email/{user_id}/{token}", status_code=status.HTTP_200_OK, name="verify_email", tags=["Login and Registration"])
async def verify_email(user_id: UUID, token: str, db: AsyncSession = Depends(get_db), email_service: EmailService = Depends(get_email_service)):
    """
    Verify user's email with a provided token.
    
    - **user_id**: UUID of the user to verify.
    - **token**: Verification token sent to the user's email.
    """
    if await UserService.verify_email_with_token(db, user_id, token):
        return {"message": "Email verified successfully"}
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token")

@router.put("/users/{user_id}/nickname/", response_model=UserUpdate, tags=["User Profile"])
async def update_nickname(user_id: UUID, nickname: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Update user's nickname.
    - **user_id**: UUID of the user to update.
    - **nickname**: New nickname.
    """
    updated_user = await UserService.update_nickname(db, user_id, nickname)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return updated_user

@router.put("/users/{user_id}/bio/", response_model=UserUpdate, tags=["User Profile"])
async def update_bio(user_id: UUID, bio: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Update user's biography.
    - **user_id**: UUID of the user to update.
    - **bio**: New biography.
    """
    updated_user = await UserService.update_bio(db, user_id, bio)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return updated_user

@router.put("/users/{user_id}/location/", response_model=UserUpdate, tags=["User Profile"])
async def update_location(user_id: UUID, location: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Update user's location.

    - **user_id**: UUID of the user to update.
    - **location**: New location.
    """
    updated_user = await UserService.update_location(db, user_id, location)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return updated_user

@router.put("/users/{user_id}/profile-picture/", response_model=UserUpdate, tags=["User Profile"])
async def update_profile_picture(user_id: UUID, profile_picture_url: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Update user's profile picture URL.

    - **user_id**: UUID of the user to update.
    - **profile_picture_url**: New profile picture URL.
    """
    updated_user = await UserService.update_profile_picture(db, user_id, profile_picture_url)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return updated_user

@router.put("/users/{user_id}/linkedin-profile/", response_model=UserUpdate, tags=["User Profile"])
async def update_linkedin_profile(user_id: UUID, linkedin_profile_url: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Update user's LinkedIn profile URL.

    - **user_id**: UUID of the user to update.
    - **linkedin_profile_url**: New LinkedIn profile URL.
    """
    updated_user = await UserService.update_linkedin_profile(db, user_id, linkedin_profile_url)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return updated_user

@router.put("/users/{user_id}/github-profile/", response_model=UserUpdate, tags=["User Profile"])
async def update_github_profile(user_id: UUID, github_profile_url: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Update user's GitHub profile URL.

    - **user_id**: UUID of the user to update.
    - **github_profile_url**: New GitHub profile URL.
    """
    updated_user = await UserService.update_github_profile(db, user_id, github_profile_url)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return updated_user

#professional update
@router.put("/users/{user_id}/professional/", response_model=UserResponse, name="upgrade_to_professional", tags=["User Management Requires (Admin or Manager Roles)"])
async def upgrade_to_professional(user_id: UUID, db: AsyncSession = Depends(get_db), email_service: EmailService = Depends(get_email_service), current_user: dict = Depends(require_role(["ADMIN", "MANAGER"]))):
    """
    Upgrade a user to professional status.

    Args:
        user_id (UUID): The ID of the user to be upgraded.
        db (AsyncSession): The database session dependency.
        email_service (EmailService): Dependency to provide email service.
        current_user (dict): The current authenticated user (must be an admin or manager).

    Returns:
        UserResponse: The updated user details with the professional role.

    Raises:
        HTTPException: If the user is not found or the current user is not authorized.
    """
    user = await UserService.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Update the user's role to 'PROFESSIONAL'
    updated_user = await UserService.update(db, user_id, {"role": UserRole.PROFESSIONAL})

    # Send notification email to the user
    await send_professional_upgrade_notification(updated_user.email, str(updated_user.role), email_service)

    return UserResponse.model_construct(
        id=updated_user.id,
        nickname=updated_user.nickname,
        first_name=updated_user.first_name,
        last_name=updated_user.last_name,
        bio=updated_user.bio,
        profile_picture_url=updated_user.profile_picture_url,
        github_profile_url=updated_user.github_profile_url,
        linkedin_profile_url=updated_user.linkedin_profile_url,
        role=updated_user.role,
        email=updated_user.email,
        last_login_at=updated_user.last_login_at,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at,
        links=create_user_links(updated_user.id, Request)  # Assuming you have a function to create HATEOAS links
    )





# Method to fetch user ID by email
async def get_user_id_by_email(db_session, email):
    """
    Fetches a user ID from the database based on the email.

    Args:
        db_session: The database session.
        email (str): The email of the user to fetch.

    Returns:
        str: The user ID if found, else None.
    """
    user = await db_session.execute(select(User.id).filter(User.email == email))
    user_id = user.scalar_one_or_none()  # Get the user ID or None if not found
    return user_id

# Example endpoint to demonstrate fetching user ID by email
@router.get("/users/{email}/id")
async def get_user_id(email: str, db: AsyncSession = Depends(get_db)):
    """
    Fetch user ID by email.

    Args:
        email (str): The email of the user.

    Returns:
        str: The user ID.
    """
    user_id = await get_user_id_by_email(db, email)
    if user_id is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user_id}

async def send_professional_upgrade_notification(user_email: str, new_role: str, email_service: EmailService):
    """
    Sends a notification email to the user when their professional status is upgraded.

    Args:
        user_email (str): The email address of the user.
        new_role (str): The new role of the user (e.g., 'PROFESSIONAL').
        email_service (EmailService): An instance of the EmailService.
    """
    subject = "Professional Status Upgrade Notification"
    message = f"Hello,\n\nYour user account has been upgraded to {new_role}.\n\nThank you for using our platform."
    
    try:
        await email_service.send_email(user_email, subject, message)
    except Exception as e:
        # Handle any exceptions that might occur during email sending
        print(f"Failed to send email notification to {user_email}: {str(e)}")


# Get user's nickname
@router.get("/users/{user_id}/nickname", tags=["User Profile"])
async def get_user_nickname(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get user's nickname by ID.
    """
    user = await db.execute(select(User.nickname).filter(User.id == user_id))
    nickname = user.scalar_one_or_none()
    if not nickname:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"nickname": nickname}

# Get user's bio
@router.get("/users/{user_id}/bio", tags=["User Profile"])
async def get_user_bio(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get user's bio by ID.
    """
    user = await db.execute(select(User.bio).filter(User.id == user_id))
    bio = user.scalar_one_or_none()
    if not bio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"bio": bio}

# Get user's location
@router.get("/users/{user_id}/location", tags=["User Profile"])
async def get_user_location(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get user's location by ID.
    """
    user = await db.execute(select(User.location).filter(User.id == user_id))
    location = user.scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"location": location}

# Get user's profile picture URL
@router.get("/users/{user_id}/profile-picture", tags=["User Profile"])
async def get_user_profile_picture(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get user's profile picture URL by ID.
    """
    user = await db.execute(select(User.profile_picture_url).filter(User.id == user_id))
    profile_picture_url = user.scalar_one_or_none()
    if not profile_picture_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"profile_picture_url": profile_picture_url}

# Get user's LinkedIn profile URL
@router.get("/users/{user_id}/linkedin-profile", tags=["User Profile"])
async def get_user_linkedin_profile(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get user's LinkedIn profile URL by ID.
    """
    user = await db.execute(select(User.linkedin_profile_url).filter(User.id == user_id))
    linkedin_profile_url = user.scalar_one_or_none()
    if not linkedin_profile_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"linkedin_profile_url": linkedin_profile_url}

# Get user's GitHub profile URL
@router.get("/users/{user_id}/github-profile", tags=["User Profile"])
async def get_user_github_profile(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get user's GitHub profile URL by ID.
    """
    user = await db.execute(select(User.github_profile_url).filter(User.id == user_id))
    github_profile_url = user.scalar_one_or_none()
    if not github_profile_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"github_profile_url": github_profile_url}


