from aiogram import Router
from .common import router as common_router
from .booking import router as booking_router
from .check import router as check_router

router = Router()
router.include_router(check_router)
router.include_router(booking_router)
router.include_router(common_router)