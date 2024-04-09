// middleware/validation.go

package middleware

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"go.mongodb.org/mongo-driver/bson"
)

func ValidateUserDetail() gin.HandlerFunc {
	return func(c *gin.Context) {
		var userDetail bson.M
		if err := c.ShouldBindJSON(&userDetail); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		// perform custom validation on userDetail

		c.Set("userDetail", userDetail)
		c.Next()
	}
}
