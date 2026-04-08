# Deploying to Render

This guide explains how to deploy the Blog Generation Pipeline to Render.

## Prerequisites

1. **GitHub Repository** - The code is already pushed to GitHub
2. **MongoDB Atlas Account** - Free tier at https://www.mongodb.com/cloud/atlas
3. **MegaLLM API Key** - Get from https://beta.megallm.io
4. **Render Account** - Create a
t https://render.com

## Step-by-Step Deployment

### 1. Set Up MongoDB Atlas

1. Create a free MongoDB cluster at https://www.mongodb.com/cloud/atlas
2. Create a database user with a strong password
3. Get your connection string (MongoDB URI)
4. Your URI will look like:
   ```
   mongodb+srv://username:password@cluster.mongodb.net/megallm_blog_platform?retryWrites=true&w=majority
   ```

### 2. Get MegaLLM API Key

1. Sign up at https://beta.megallm.io
2. Generate an API key
3. The claude-opus-4-6 model is used for high-quality content generation

### 3. Deploy on Render

#### Option A: Using Render Dashboard (Point & Click)

1. Go to https://dashboard.render.com
2. Click "New +" → "Web Service"
3. Connect your GitHub repository (authorize if needed)
4. Select the `megallmblogv2` repository
5. Configure the deployment:
   - **Name:** `megallm-blog-platform`
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn --workers 4 --timeout 120 wsgi:app`
   - **Plan:** Free (or Paid for production)

6. Add Environment Variables:
   ```
   MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/megallm_blog_platform?retryWrites=true&w=majority
   MEGALLM_API_KEY=sk-mega-YOUR_API_KEY
   MODEL=claude-opus-4-6
   MONGODB_DB=megallm_blog_platform
   FLASK_ENV=production
   DEBUG=False
   SECRET_KEY=<generate-a-random-string-here>
   ```

7. Click "Create Web Service"
8. Wait for deployment (typically 3-5 minutes)
9. Your app will be live at `megallm-blog-platform.onrender.com`

#### Option B: Using render.yaml (Infrastructure as Code)

If your Render plan supports it (Pro or higher):

1. Render will automatically detect `render.yaml`
2. Add the required environment variables in the Render dashboard
3. Push to GitHub:
   ```bash
   git add Procfile render.yaml RENDER_DEPLOYMENT.md
   git commit -m "Add Render deployment configuration"
   git push origin main
   ```
4. Connect repository to Render - it will use `render.yaml` automatically

### 4. Set Environment Variables on Render

On the Render dashboard for your service:

1. Go to "Environment" tab
2. Add these variables:
   - `MONGODB_URI` - Your MongoDB Atlas connection string
   - `MEGALLM_API_KEY` - Your MegaLLM API key
   - `FLASK_ENV` - Set to `production`
   - `DEBUG` - Set to `False`
   - `SECRET_KEY` - Generate a random string (use a secure generator)

**Note:** Don't include quotes around values in Render's environment variable form.

### 5. Access Your Application

- Your app will be accessible at: `https://megallm-blog-platform.onrender.com`
- The free tier may have a brief startup delay if inactive for 15 minutes
- **API Endpoints:**
  - `GET /` - Health check
  - `POST /generate-blogs` - Generate blogs
  - `GET /blog/:id` - Get blog details
  - `GET /accounts` - List accounts

## Monitoring & Logs

1. Go to "Logs" tab in Render dashboard
2. View real-time application logs
3. Check for errors or startup issues

## Troubleshooting

### App starts but crashes
- Check logs in Render dashboard
- Verify all environment variables are set correctly
- Ensure MongoDB URI is correct (test locally first)

### "Module not found" errors
- Make sure `requirements.txt` has all dependencies
- Run `pip install -r requirements.txt` locally to verify

### Database connection fails
- Verify `MONGODB_URI` is correct
- Check MongoDB Atlas firewall settings
- Add Render's IP to MongoDB Atlas (or allow all IPs for development)

### 502 Bad Gateway
- Usually means the app crashed during startup
- Check logs in Render
- Verify all required environment variables are set

## Upgrading from Free Plan

For production use:
- **Free Plan:** Limited to 0.5 CPU and 512 MB RAM
- **Starter Plan:** 1 CPU, 2 GB RAM (recommended for this app)
- **Standard Plan:** 2 CPU, 4 GB RAM (for high traffic)

To upgrade:
1. Go to your service settings on Render
2. Click "Change Plan"
3. Select your desired plan

## Next Steps

After deployment:
1. Test the API manually using the endpoints
2. Monitor logs and performance
3. Set up automated blog generation using Render's scheduled jobs (if needed)
4. Update your domain configuration if using a custom domain

## Support

- Render Docs: https://render.com/docs
- Troubleshooting: https://render.com/docs/troubleshooting
