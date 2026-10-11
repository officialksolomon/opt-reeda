@description('The Azure region where resources will be deployed.')
param location string = resourceGroup().location

@description('Name prefix for resources.')
param environmentName string = 'optreeda-prod'

@description('PostgreSQL database connection string (e.g. from Neon, Render, or Supabase).')
@secure()
param databaseUrl string = ''

@description('Optional Redis connection URL. If empty, Django defaults to in-memory cache.')
@secure()
param redisUrl string = ''

@description('Django SECRET_KEY for cryptographic signing.')
@secure()
param djangoSecretKey string = newGuid()

@description('Optional pre-built image to deploy. If empty, points to ACR optreeda:latest.')
param webImage string = ''

// Optional third-party credentials (safe fallbacks ensure deployment succeeds if unconfigured)
@secure()
param paystackSecretKey string = ''
param paystackPublicKey string = ''

param cloudinaryCloudName string = ''
param cloudinaryApiKey string = ''
@secure()
param cloudinaryApiSecret string = ''

param emailHost string = 'smtp.gmail.com'
param emailPort int = 587
param emailHostUser string = ''
@secure()
param emailHostPassword string = ''
param emailUseTls bool = true

// ---------------------------------------------------------------------------
// 1. Log Analytics Workspace
// ---------------------------------------------------------------------------
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: take('log-${uniqueString(resourceGroup().id)}', 63)
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// ---------------------------------------------------------------------------
// 2. Azure Container Registry (ACR)
// ---------------------------------------------------------------------------
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: take('acr${uniqueString(resourceGroup().id)}', 50)
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// ---------------------------------------------------------------------------
// 3. Azure Container Apps Managed Environment
// ---------------------------------------------------------------------------
resource containerAppsEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: take('${environmentName}-env', 60)
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// ---------------------------------------------------------------------------
// 4. Configuration
// ---------------------------------------------------------------------------
var resolvedImage = !empty(webImage) ? webImage : '${containerRegistry.properties.loginServer}/optreeda:latest'

// ---------------------------------------------------------------------------
// 5. Container App (Single Container for ACA Express / Consumption tier)
// ---------------------------------------------------------------------------
resource webApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'optreeda-web'
  location: location
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 5000
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          username: containerRegistry.listCredentials().username
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
        {
          name: 'django-secret-key'
          value: djangoSecretKey
        }
        {
          name: 'database-url'
          value: !empty(databaseUrl) ? databaseUrl : 'placeholder'
        }
        {
          name: 'redis-url'
          value: !empty(redisUrl) ? redisUrl : 'placeholder'
        }
        {
          name: 'paystack-secret-key'
          value: !empty(paystackSecretKey) ? paystackSecretKey : 'placeholder'
        }
        {
          name: 'cloudinary-api-secret'
          value: !empty(cloudinaryApiSecret) ? cloudinaryApiSecret : 'placeholder'
        }
        {
          name: 'email-host-password'
          value: !empty(emailHostPassword) ? emailHostPassword : 'placeholder'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'web'
          image: resolvedImage
          command: [
            '/start'
          ]
          resources: {
            cpu: json('0.5')
            memory: '1.0Gi'
          }
          env: [
            {
              name: 'PORT'
              value: '5000'
            }
            {
              name: 'DJANGO_SETTINGS_MODULE'
              value: 'config.settings.production'
            }
            {
              name: 'DJANGO_SECRET_KEY'
              secretRef: 'django-secret-key'
            }
            {
              name: 'DJANGO_ALLOWED_HOSTS'
              value: '*'
            }
            {
              name: 'DJANGO_CSRF_TRUSTED_ORIGINS'
              value: 'https://*.azurecontainerapps.io'
            }
            {
              name: 'DJANGO_ADMIN_URL'
              value: 'admin/'
            }
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'REDIS_URL'
              secretRef: 'redis-url'
            }
            {
              name: 'CELERY_TASK_ALWAYS_EAGER'
              value: 'True'
            }
            {
              name: 'PAYSTACK_PUBLIC_KEY'
              value: paystackPublicKey
            }
            {
              name: 'PAYSTACK_SECRET_KEY'
              secretRef: 'paystack-secret-key'
            }
            {
              name: 'CLOUDINARY_CLOUD_NAME'
              value: cloudinaryCloudName
            }
            {
              name: 'CLOUDINARY_API_KEY'
              value: cloudinaryApiKey
            }
            {
              name: 'CLOUDINARY_API_SECRET'
              secretRef: 'cloudinary-api-secret'
            }
            {
              name: 'EMAIL_HOST'
              value: emailHost
            }
            {
              name: 'EMAIL_PORT'
              value: string(emailPort)
            }
            {
              name: 'EMAIL_HOST_USER'
              value: emailHostUser
            }
            {
              name: 'EMAIL_HOST_PASSWORD'
              secretRef: 'email-host-password'
            }
            {
              name: 'EMAIL_USE_TLS'
              value: string(emailUseTls)
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
output WEB_URL string = 'https://${webApp.properties.configuration.ingress.fqdn}'
output ACR_LOGIN_SERVER string = containerRegistry.properties.loginServer
output ACR_NAME string = containerRegistry.name
