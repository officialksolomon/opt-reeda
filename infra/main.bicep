@description('The Azure region where resources will be deployed.')
param location string = resourceGroup().location

@description('Name prefix for resources.')
param environmentName string = 'optreeda-prod'

@description('Django SECRET_KEY for cryptographic signing.')
@secure()
param djangoSecretKey string = newGuid()

@description('PostgreSQL administrative username.')
param dbAdminUser string = 'optreeda'

@description('PostgreSQL administrative password.')
@secure()
param dbAdminPassword string = 'P@ss_${uniqueString(resourceGroup().id)}123!'

@description('PostgreSQL database name.')
param dbName string = 'optreeda'

@description('Optional pre-built image to deploy. If empty, points to ACR optreeda:latest.')
param webImage string = ''

@description('Whether to deploy a separate Celery background worker container.')
param deployCeleryWorker bool = false

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
// 4. Azure Database for PostgreSQL Flexible Server
// ---------------------------------------------------------------------------
resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: take('psql-${uniqueString(resourceGroup().id)}', 63)
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    administratorLogin: dbAdminUser
    administratorLoginPassword: dbAdminPassword
    version: '15'
    storage: {
      storageSizeGB: 32
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

resource postgresDb 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  parent: postgresServer
  name: dbName
  properties: {
    charset: 'utf8'
    collation: 'en_US.utf8'
  }
}

// Allow internal traffic from all Azure services (including Container Apps)
resource allowAzureIps 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-03-01-preview' = {
  parent: postgresServer
  name: 'AllowAllAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// ---------------------------------------------------------------------------
// 5. Azure Cache for Redis
// ---------------------------------------------------------------------------
resource redisCache 'Microsoft.Cache/redis@2023-08-01' = {
  name: take('redis-${uniqueString(resourceGroup().id)}', 63)
  location: location
  properties: {
    sku: {
      name: 'Basic'
      family: 'C'
      capacity: 0
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
  }
}

// ---------------------------------------------------------------------------
// 6. Application Configuration & Variables
// ---------------------------------------------------------------------------
var resolvedImage = !empty(webImage) ? webImage : '${containerRegistry.properties.loginServer}/optreeda:latest'
var dbUrl = 'postgres://${dbAdminUser}:${dbAdminPassword}@${postgresServer.properties.fullyQualifiedDomainName}:5432/${dbName}?sslmode=require'
var redisUrl = 'rediss://:${redisCache.listKeys().primaryKey}@${redisCache.properties.hostName}:6380/0'

// ---------------------------------------------------------------------------
// 7. Web Container App (optreeda-web)
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
          value: dbUrl
        }
        {
          name: 'redis-url'
          value: redisUrl
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
              value: deployCeleryWorker ? 'False' : 'True'
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
        maxReplicas: 3
      }
    }
  }
}

// ---------------------------------------------------------------------------
// 8. Celery Worker Container App (optreeda-worker, optional)
// ---------------------------------------------------------------------------
resource workerApp 'Microsoft.App/containerApps@2023-05-01' = if (deployCeleryWorker) {
  name: 'optreeda-worker'
  location: location
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
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
          value: dbUrl
        }
        {
          name: 'redis-url'
          value: redisUrl
        }
        {
          name: 'cloudinary-api-secret'
          value: !empty(cloudinaryApiSecret) ? cloudinaryApiSecret : 'placeholder'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'worker'
          image: resolvedImage
          command: [
            '/start-celeryworker'
          ]
          resources: {
            cpu: json('0.5')
            memory: '1.0Gi'
          }
          env: [
            {
              name: 'DJANGO_SETTINGS_MODULE'
              value: 'config.settings.production'
            }
            {
              name: 'DJANGO_SECRET_KEY'
              secretRef: 'django-secret-key'
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
              value: 'False'
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
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
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
output POSTGRES_SERVER string = postgresServer.properties.fullyQualifiedDomainName
output REDIS_HOST string = redisCache.properties.hostName
