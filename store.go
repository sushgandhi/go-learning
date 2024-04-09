// middleware/store.go

package middleware

import (
	"github.com/gin-gonic/gin"
	"github.com/yourusername/yourproject/store"
	"go.mongodb.org/mongo-driver/mongo"
)

func WithUserStore(collection *mongo.Collection) gin.HandlerFunc {
	return func(c *gin.Context) {
		userStore := &store.MongoUserStore{collection: collection}
		c.Set("userStore", userStore)
		c.Next()
	}
}
