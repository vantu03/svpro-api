from fastapi import HTTPException
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, require_user
from app.models.post_attachment import PostAttachment
from app.models.post_comment import PostComment
from app.models.post_interacts import PostInteract
from app.models.user import User
from app.schemas.comment import CommentCreate
from app.schemas.post import PostCreate
from app.utils import response_json, build_response, to_dict
from sqlalchemy import select, func, case, distinct
from app.models.post import Post
from app.models.post_view import PostView

router = APIRouter()


@router.get("/news")
async def get_new_posts(
    initial: bool = True,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    viewed_result = await db.execute(
        select(PostView.post_id).where(PostView.user_id == user.id)
    )
    viewed_post_ids = [pid for (pid,) in viewed_result.all()]

    stmt = (
        select(
            Post.id,
            Post.content,
            Post.user_id,
            User.full_name.label("user_full_name"),
            User.avatar_url.label("user_avatar_url"),
            Post.views,
            Post.created_at,
            Post.updated_at,
            Post.is_deleted,
            func.count(distinct(PostInteract.id)).label("interact_count"),
            func.count(distinct(PostComment.id)).label("comment_count"),
            (func.max(case((PostInteract.user_id == user.id, 1), else_=0)) > 0).label("is_interact")
        )
        .join(User, User.id == Post.user_id)
        .join(PostInteract, PostInteract.post_id == Post.id, isouter=True)
        .join(PostComment, PostComment.post_id == Post.id, isouter=True)
        .where(Post.is_deleted.is_(False))
        .group_by(Post.id, Post.content, Post.user_id, User.full_name, Post.created_at, Post.updated_at)
        .order_by(Post.created_at.desc())
        .limit(10)
    )

    # Giữ lại bài của chính người dùng, bỏ bài đã xem của người khác
    if viewed_post_ids:
        stmt = stmt.where(
            (~Post.id.in_(viewed_post_ids)) | (Post.user_id == user.id)
        )

    result = await db.execute(stmt)
    posts = result.mappings().all()

    post_dicts = [dict(row) for row in posts]

    if not post_dicts or not initial:
        return build_response(detail=response_json(True, data=[]))

    post_ids = [p["id"] for p in post_dicts]

    attach_stmt = select(
        PostAttachment.id,
        PostAttachment.post_id,
        PostAttachment.type,
        PostAttachment.url,
        PostAttachment.created_at,
        PostAttachment.updated_at,
    ).where(PostAttachment.post_id.in_(post_ids))

    attach_result = await db.execute(attach_stmt)
    attachments = attach_result.mappings().all()

    attach_map = {}
    for att in attachments:
        attach_map.setdefault(att["post_id"], []).append(dict(att))

    for p in post_dicts:
        p["attachments"] = attach_map.get(p["id"], [])

    return build_response(detail=response_json(True, data=post_dicts))


@router.post("/create")
async def create_post(
        data: PostCreate,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(require_user),
):
    new_post = Post(
        user_id=user.id,
        content=data.content,
    )
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post)

    # Lấy dữ liệu format giống news
    stmt = (
        select(
            Post.id,
            Post.content,
            Post.user_id,
            User.full_name.label("user_full_name"),
            User.avatar_url.label("user_avatar_url"),
            Post.views,
            Post.created_at,
            Post.updated_at,
            Post.is_deleted,
            func.count(distinct(PostInteract.id)).label("interact_count"),
            func.count(distinct(PostComment.id)).label("comment_count"),
            (func.max(case((PostInteract.user_id == user.id, 1), else_=0)) > 0).label("is_interact")
        )
        .join(User, User.id == Post.user_id)
        .join(PostInteract, PostInteract.post_id == Post.id, isouter=True)
        .join(PostComment, PostComment.post_id == Post.id, isouter=True)
        .where(Post.id == new_post.id)
        .group_by(Post.id, Post.content, Post.user_id, User.full_name, Post.created_at, Post.updated_at, Post.is_deleted)
    )
    result = await db.execute(stmt)
    row = result.mappings().first()

    return build_response(
        detail=response_json(True, data=to_dict(row))
    )

@router.delete("/{post_id}/delete")
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=404, detail="Bài viết không tồn tại")

    # Quyền xoá: chủ post hoặc superuser
    if post.user_id != user.id and not user.is_superuser:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xoá bài viết này")

    # Soft delete
    post.is_deleted = True
    await db.commit()

    return build_response(
        detail=response_json(True, data={"status": "deleted", "id": post_id})
    )
@router.get("/{post_id}/comments")
async def get_comments(
    post_id: int,
    offset: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    result = await db.execute(
        select(
            PostComment.id,
            PostComment.post_id,
            PostComment.user_id,
            PostComment.content,
            PostComment.is_deleted,
            PostComment.created_at,
            PostComment.updated_at,
            User.full_name.label("user_full_name"),
            User.avatar_url.label("user_avatar_url"),
        )
        .join(User, User.id == PostComment.user_id)
        .where(
            PostComment.post_id == post_id,
            PostComment.is_deleted.is_(False)
        )
        .order_by(PostComment.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    comments = result.mappings().all()

    return build_response(
        detail=response_json(
            True,
            data=[dict(row) for row in comments]
        )
    )

@router.post("/{post_id}/comment/create")
async def create_comment(
    post_id: int,
    payload: CommentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    # Kiểm tra post tồn tại và chưa xoá
    result = await db.execute(
        select(Post).where(Post.id == post_id, Post.is_deleted.is_(False))
    )
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=404, detail="Bài viết không còn tồn tại")

    # Tạo comment mới
    new_comment = PostComment(
        post_id=post_id,
        user_id=user.id,
        content=payload.content,
    )
    db.add(new_comment)
    await db.commit()
    await db.refresh(new_comment)

    stmt = (
        select(
            PostComment.id,
            PostComment.post_id,
            PostComment.user_id,
            PostComment.content,
            PostComment.is_deleted,
            PostComment.created_at,
            PostComment.updated_at,
            User.full_name.label("user_full_name"),
            User.avatar_url.label("user_avatar_url"),
        )
        .join(User, User.id == PostComment.user_id)
        .where(PostComment.id == new_comment.id)
    )
    result = await db.execute(stmt)
    row = result.mappings().first()

    return build_response(
        detail=response_json(
            True,
            data=dict(row)
        )
    )

@router.delete("/{post_id}/comment/{comment_id}/delete")
async def delete_comment(
    post_id: int,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    # Tìm comment
    result = await db.execute(
        select(PostComment).where(
            PostComment.id == comment_id,
            PostComment.post_id == post_id
        )
    )
    comment = result.scalars().first()
    if not comment:
        raise HTTPException(status_code=404, detail="Bình luận không tồn tại")

    # Kiểm tra quyền xoá (chủ comment hoặc superuser)
    if comment.user_id != user.id and not user.is_superuser:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xoá bình luận này")

    # Soft delete
    comment.is_deleted = True
    await db.commit()

    return build_response(
        detail=response_json(
            True,
            data={"status": "deleted", "id": comment_id}
        )
    )
@router.post("/{post_id}/interact")
async def interact_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    # Kiểm tra post
    result = await db.execute(
        select(Post).where(Post.id == post_id, Post.is_deleted.is_(False))
    )
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=404, detail="Bài viết không tồn tại")

    result = await db.execute(
        select(PostInteract).where(
            PostInteract.post_id == post_id,
            PostInteract.user_id == user.id
        )
    )
    interact = result.scalars().first()

    if interact:
        await db.delete(interact)
        await db.commit()

        # Đếm lại số lượt like
        count_result = await db.execute(
            select(func.count(PostInteract.id)).where(PostInteract.post_id == post_id)
        )
        count = count_result.scalar()

        return build_response(detail=response_json(
            True,
            data={"post_id": post_id, "is_interact": False, "interact_count": count}
        ))
    else:
        new_interact = PostInteract(post_id=post_id, user_id=user.id)
        db.add(new_interact)
        await db.commit()
        await db.refresh(new_interact)

        count_result = await db.execute(
            select(func.count(PostInteract.id)).where(PostInteract.post_id == post_id)
        )
        count = count_result.scalar()

        return build_response(detail=response_json(
            True,
            data={"post_id": post_id, "is_interact": True, "interact_count": count}
        ))


@router.post("/{post_id}/view")
async def add_view(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    # Kiểm tra post tồn tại và chưa xoá
    result = await db.execute(
        select(Post).where(Post.id == post_id, Post.is_deleted.is_(False))
    )
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=404, detail="Bài viết không tồn tại")

    # Kiểm tra đã view chưa
    result = await db.execute(
        select(PostView).where(
            PostView.post_id == post_id,
            PostView.user_id == user.id
        )
    )
    view = result.scalars().first()
    if view:
        return build_response(
            detail=response_json(status=True, data={"status": "already_viewed", "post_id": post_id})
        )



    # Tạo view mới
    new_view = PostView(
        post_id=post_id,
        user_id=user.id
    )

    #Tăng view
    post.views += 1

    db.add(new_view)
    await db.commit()
    await db.refresh(new_view)

    return build_response(
        detail=response_json(status=True, data=to_dict(new_view))
    )